# Copyright 2021 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import asyncio
import simbricks.utils.graphlib as graphlib
from collections import defaultdict
import simbricks.exectools as exectools
import simbricks.proxy
import shlex
import time
import itertools
import json
import traceback

class Experiment(object):
    name = None
    timeout = None
    checkpoint = False
    no_simbricks = False

    def __init__(self, name):
        self.name = name
        self.hosts = []
        self.nics = []
        self.networks = []
        self.metadata = {}

    def add_host(self, sim):
        for h in self.hosts:
            if h.name == sim.name:
                raise Exception('Duplicate host name')
        self.hosts.append(sim)

    def add_nic(self, sim):
        for n in self.nics:
            if n.name == sim.name:
                raise Exception('Duplicate nic name')
        self.nics.append(sim)

    def add_network(self, sim):
        for n in self.networks:
            if n.name == sim.name:
                raise Exception('Duplicate net name')
        self.networks.append(sim)

    def all_simulators(self):
        """ All simulators used in experiment. """
        return itertools.chain(self.hosts, self.nics, self.networks)

    def resreq_mem(self):
        mem = 0
        for s in self.all_simulators():
            mem += s.resreq_mem()
        return mem

    def resreq_cores(self):
        cores = 0
        for s in self.all_simulators():
            cores += s.resreq_cores()
        return cores

class DistributedExperiment(Experiment):
    num_hosts = 1
    host_mapping = None
    proxies_listen = None
    proxies_connect = None

    def __init__(self, name, num_hosts):
        self.num_hosts = num_hosts
        self.host_mapping = {}
        self.proxies_listen = []
        self.proxies_connect = []
        super().__init__(name)

    def add_proxy(self, proxy):
        if proxy.listen:
            self.proxies_listen.append(proxy)
        else:
            self.proxies_connect.append(proxy)

    def all_simulators(self):
        return itertools.chain(super().all_simulators(),
                self.proxies_listen, self.proxies_connect)

    def assign_sim_host(self, sim, host):
        """ Assign host ID (< self.num_hosts) for a simulator. """
        assert(host >= 0 and host < self.num_hosts)
        self.host_mapping[sim] = host


    def all_sims_assigned(self):
        """ Check if all simulators are assigned to a host. """
        for s in self.all_simulators():
            if s not in self.host_mapping:
                return False
        return True


class ExperimentBaseRunner(object):
    def __init__(self, exp, env, verbose):
        self.exp = exp
        self.env = env
        self.verbose = verbose
        self.out = ExpOutput(exp)
        self.running = []
        self.sockets = []
        self.wait_sims = []

    def sim_executor(self, sim):
        raise NotImplementedError("Please implement this method")

    def sim_graph(self):
        sims = self.exp.all_simulators()
        graph = {}
        for sim in sims:
            deps = sim.dependencies() + sim.extra_deps
            graph[sim] = set()
            for d in deps:
                graph[sim].add(d)
        return graph

    async def start_sim(self, sim):
        """ Start a simulator and wait for it to be ready. """

        name = sim.full_name()
        if self.verbose:
            print('%s: starting %s' % (self.exp.name, name))

        # run simulator
        exec = self.sim_executor(sim)
        sc = exec.create_component(name,
                    shlex.split(sim.run_cmd(self.env)), verbose=self.verbose,
                    canfail=True)
        await sc.start()
        self.running.append((sim, sc))

        # add sockets for cleanup
        for s in sim.sockets_cleanup(self.env):
            self.sockets.append((exec, s))

        # Wait till sockets exist
        wait_socks = sim.sockets_wait(self.env)
        if wait_socks:
            if self.verbose:
                print('%s: waiting for sockets %s' % (self.exp.name, name))

            await exec.await_files(wait_socks, verbose=self.verbose)

        # add time delay if required
        delay = sim.start_delay()
        if delay > 0:
            await asyncio.sleep(delay)

        if sim.wait_terminate():
            self.wait_sims.append(sc)

        if self.verbose:
            print('%s: started %s' % (self.exp.name, name))

    async def before_wait(self):
        pass

    async def before_cleanup(self):
        pass

    async def after_cleanup(self):
        pass


    async def prepare(self):
        # generate config tars
        copies = []
        for host in self.exp.hosts:
            path = self.env.cfgtar_path(host)
            if self.verbose:
                print('preparing config tar:', path)
            host.node_config.make_tar(path)
            copies.append(self.sim_executor(host).send_file(path, self.verbose))
        await asyncio.wait(copies)

        # prepare all simulators in parallel
        sims = []
        for sim in self.exp.all_simulators():
            prep_cmds = [pc for pc in sim.prep_cmds(self.env)]
            exec = self.sim_executor(sim)
            sims.append(exec.run_cmdlist('prepare_' + self.exp.name, prep_cmds,
                verbose=self.verbose))
        await asyncio.wait(sims)

    async def wait_for_sims(self):
        """ Wait for simulators to terminate (the ones marked to wait on). """
        if self.verbose:
            print('%s: waiting for hosts to terminate' % self.exp.name)
        for sc in self.wait_sims:
            await sc.wait()

    async def run(self):
        try:
            self.out.set_start()

            graph = self.sim_graph()
            ts = graphlib.TopologicalSorter(graph)
            ts.prepare()
            while ts.is_active():
                # start ready simulators in parallel
                starts = []
                sims = []
                for sim in ts.get_ready():
                    starts.append(self.start_sim(sim))
                    sims.append(sim)

                # wait for starts to complete
                await asyncio.wait(starts)

                for sim in sims:
                    ts.done(sim)

            await self.before_wait()
            await self.wait_for_sims()
        except:
            self.out.set_failed()
            traceback.print_exc()

        finally:
            self.out.set_end()

            # shut things back down
            if self.verbose:
                print('%s: cleaning up' % self.exp.name)

            await self.before_cleanup()

            # "interrupt, terminate, kill" all processes
            scs = []
            for _,sc in self.running:
                scs.append(sc.int_term_kill())
            await asyncio.wait(scs)

            # wait for all processes to terminate
            for _,sc in self.running:
                await sc.wait()

            # remove all sockets
            scs = []
            for (exec,sock) in self.sockets:
                scs.append(exec.rmtree(sock))
            await asyncio.wait(scs)

            # add all simulator components to the output
            for sim,sc in self.running:
                self.out.add_sim(sim, sc)

            await self.after_cleanup()
        return self.out


class ExperimentSimpleRunner(ExperimentBaseRunner):
    """ Simple experiment runner with just one executor. """
    def __init__(self, exec, *args, **kwargs):
        self.exec = exec
        super().__init__(*args, **kwargs)

    def sim_executor(self, sim):
        return self.exec


class ExperimentDistributedRunner(ExperimentBaseRunner):
    """ Simple experiment runner with just one executor. """
    def __init__(self, execs, *args, **kwargs):
        self.execs = execs
        super().__init__(*args, **kwargs)
        assert self.exp.num_hosts <= len(execs)

    def sim_executor(self, sim):
        h_id = self.exp.host_mapping[sim]
        return self.execs[h_id]

    async def prepare(self):
        # make sure all simulators are assigned to an executor
        assert(self.exp.all_sims_assigned())

        # set IP addresses for proxies based on assigned executors
        for p in itertools.chain(
                self.exp.proxies_listen, self.exp.proxies_connect):
            exec = self.sim_executor(p)
            p.ip = exec.ip

        await super().prepare()


class ExpEnv(object):
    def __init__(self, repo_path, workdir, cpdir):
        self.repodir = os.path.abspath(repo_path)
        self.workdir = os.path.abspath(workdir)
        self.cpdir = os.path.abspath(cpdir)
        self.qemu_img_path = self.repodir + '/sims/external/qemu/build/qemu-img'
        self.qemu_path = self.repodir + '/sims/external/qemu/build/x86_64-softmmu/qemu-system-x86_64'
        self.qemu_kernel_path = self.repodir + '/images/bzImage'
        self.gem5_path = self.repodir + '/sims/external/gem5/build/X86/gem5.fast'
        self.gem5_py_path = self.repodir + '/sims/external/gem5/configs/simbricks/simbricks.py'
        self.gem5_kernel_path = self.repodir + '/images/vmlinux'

    def hdcopy_path(self, sim):
        return '%s/hdcopy.%s' % (self.workdir, sim.name)

    def hd_path(self, hd_name):
        return '%s/images/output-%s/%s' % (self.repodir, hd_name, hd_name)

    def hd_raw_path(self, hd_name):
        return '%s/images/output-%s/%s.raw' % (self.repodir, hd_name, hd_name)

    def cfgtar_path(self, sim):
        return '%s/cfg.%s.tar' % (self.workdir, sim.name)

    def nic_pci_path(self, sim):
        return '%s/nic.pci.%s' % (self.workdir, sim.name)

    def nic_eth_path(self, sim):
        return '%s/nic.eth.%s' % (self.workdir, sim.name)

    def nic_shm_path(self, sim):
        return '%s/nic.shm.%s' % (self.workdir, sim.name)

    def n2n_eth_path(self, sim_l, sim_c):
        return '%s/n2n.eth.%s.%s' % (self.workdir, sim_l.name, sim_c.name)

    def proxy_shm_path(self, sim):
        return '%s/proxy.shm.%s' % (self.workdir, sim.name)

    def gem5_outdir(self, sim):
        return '%s/gem5-out.%s' % (self.workdir, sim.name)

    def gem5_cpdir(self, sim):
        return '%s/gem5-cp.%s' % (self.cpdir, sim.name)

class ExpOutput(object):
    def __init__(self, exp):
        self.exp_name = exp.name
        self.metadata = exp.metadata
        self.start_time = None
        self.end_time = None
        self.sims = {}
        self.success = True

    def set_start(self):
        self.start_time = time.time()

    def set_end(self):
        self.end_time = time.time()

    def set_failed(self):
        self.success = False

    def add_sim(self, sim, comp):
        obj = {
            'class': sim.__class__.__name__,
            'cmd': comp.cmd_parts,
            'stdout': comp.stdout,
            'stderr': comp.stderr,
        }
        self.sims[sim.full_name()] = obj

    def dumps(self):
        return json.dumps(self.__dict__)
