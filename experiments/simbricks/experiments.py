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
import simbricks.exectools as exectools
import shlex
import time
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

    def resreq_mem(self):
        mem = 0
        for h in self.hosts:
            mem += h.resreq_mem()
        for n in self.nics:
            mem += n.resreq_mem()
        for n in self.networks:
            mem += n.resreq_mem()
        return mem

    def resreq_cores(self):
        cores = 0
        for h in self.hosts:
            cores += h.resreq_cores()
        for n in self.nics:
            cores += n.resreq_cores()
        for n in self.networks:
            cores += n.resreq_cores()
        return cores


class ExperimentBaseRunner(object):
    def __init__(self, exp, env, verbose):
        self.exp = exp
        self.env = env
        self.verbose = verbose
        self.out = ExpOutput(exp)
        self.running = []
        self.sockets = []
        self.wait_hosts = []

    def sim_executor(self, sim):
        raise NotImplementedError("Please implement this method")

    async def before_nics(self):
        pass

    async def before_nets(self):
        pass

    async def before_hosts(self):
        pass

    async def before_wait(self):
        pass

    async def before_cleanup(self):
        pass

    async def after_cleanup(self):
        pass


    async def prepare(self):
        # generate config tars
        for host in self.exp.hosts:
            path = self.env.cfgtar_path(host)
            if self.verbose:
                print('preparing config tar:', path)
            host.node_config.make_tar(path)
            await self.sim_executor(host).send_file(path, self.verbose)

        # prepare all simulators in parallel
        sims = []
        for sim in self.exp.hosts + self.exp.nics + self.exp.networks:
            prep_cmds = [pc for pc in sim.prep_cmds(self.env)]
            exec = self.sim_executor(sim)
            sims.append(exec.run_cmdlist('prepare_' + self.exp.name, prep_cmds,
                verbose=self.verbose))
        await asyncio.wait(sims)

    async def run_nics(self):
        """ Start all NIC simulators. """
        if self.verbose:
            print('%s: starting NICS' % self.exp.name)
        for nic in self.exp.nics:
            if self.verbose:
                print('start NIC:', nic.run_cmd(self.env))
            exec = self.sim_executor(nic)
            sc = exec.create_component(nic.full_name(),
                    shlex.split(nic.run_cmd(self.env)), verbose=self.verbose,
                    canfail=True)
            await sc.start()
            self.running.append((nic, sc))

            self.sockets.append((exec, self.env.nic_pci_path(nic)))
            self.sockets.append((exec, self.env.nic_eth_path(nic)))
            self.sockets.append((exec, self.env.nic_shm_path(nic)))

        # Wait till all NIC sockets exist
        if self.verbose:
            print('%s: waiting for sockets' % self.exp.name)
        for (exec, s) in self.sockets:
            await exec.await_file(s, verbose=self.verbose)

        # just a bit of a safety delay
        await asyncio.sleep(0.5)

    async def run_nets(self):
        """ Start all network simulators (typically one). """
        if self.verbose:
            print('%s: starting networks' % self.exp.name)
        for net in self.exp.networks:
            if self.verbose:
                print('start Net:', net.run_cmd(self.env))

            exec = self.sim_executor(net)
            sc = exec.create_component(net.full_name(),
                    shlex.split(net.run_cmd(self.env)), verbose=self.verbose,
                    canfail=True)
            await sc.start()
            self.running.append((net, sc))

    async def run_hosts(self):
        """ Start all host simulators. """
        if self.verbose:
            print('%s: starting hosts' % self.exp.name)
        for host in self.exp.hosts:
            if self.verbose:
                print('start Host:', host.run_cmd(self.env))

            exec = self.sim_executor(host)
            sc = exec.create_component(host.full_name(),
                    shlex.split(host.run_cmd(self.env)), verbose=self.verbose,
                    canfail=True)
            await sc.start()
            self.running.append((host,sc))

            if host.wait:
                self.wait_hosts.append(sc)

            if host.sleep > 0:
                await asyncio.sleep(host.sleep)

    async def wait_for_hosts(self):
        """ Wait for hosts to terminate (the ones marked to wait on). """
        if self.verbose:
            print('%s: waiting for hosts to terminate' % self.exp.name)
        for sc in self.wait_hosts:
            await sc.wait()

    async def run(self):
        try:
            self.out.set_start()

            await self.before_nics()
            await self.run_nics()

            await self.before_nets()
            await self.run_nets()

            await self.before_hosts()
            await self.run_hosts()

            await self.before_wait()
            await self.wait_for_hosts()
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
            for (exec,sock) in self.sockets:
                await exec.rmtree(sock)

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