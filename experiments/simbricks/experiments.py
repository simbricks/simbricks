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

    async def prepare(self, env, verbose=False):
        # generate config tars
        for host in self.hosts:
            path = env.cfgtar_path(host)
            if verbose:
                print('preparing config tar:', path)
            host.node_config.make_tar(path)

        # prepare all simulators in parallel
        sims = []
        for sim in self.hosts + self.nics + self.networks:
            prep_cmds = [pc for pc in sim.prep_cmds(env)]
            sims.append(exectools.run_cmdlist('prepare_' + self.name, prep_cmds,
                verbose=verbose))
        await asyncio.wait(sims)

    async def run(self, env, verbose=False):
        running = []
        sockets = []
        out = ExpOutput(self)
        try:
            out.set_start()

            if verbose:
                print('%s: starting NICS' % self.name)
            for nic in self.nics:
                if verbose:
                    print('start NIC:', nic.run_cmd(env))
                sc = exectools.SimpleComponent(nic.full_name(),
                        shlex.split(nic.run_cmd(env)), verbose=verbose, canfail=True)
                await sc.start()
                running.append((nic, sc))

                sockets.append(env.nic_pci_path(nic))
                sockets.append(env.nic_eth_path(nic))
                sockets.append(env.nic_shm_path(nic))

            if verbose:
                print('%s: waiting for sockets' % self.name)

            for s in sockets:
                await exectools.await_file(s, verbose=verbose)
            await asyncio.sleep(0.5)


            # start networks
            for net in self.networks:
                if verbose:
                    print('start Net:', net.run_cmd(env))

                sc = exectools.SimpleComponent(net.full_name(),
                        shlex.split(net.run_cmd(env)), verbose=verbose, canfail=True)
                await sc.start()
                running.append((net, sc))

            # start hosts
            wait_hosts = []
            for host in self.hosts:
                if verbose:
                    print('start Host:', host.run_cmd(env))

                sc = exectools.SimpleComponent(host.full_name(),
                        shlex.split(host.run_cmd(env)), verbose=verbose, canfail=True)
                await sc.start()
                running.append((host,sc))

                if host.wait:
                    wait_hosts.append(sc)

                if host.sleep > 0:
                    await asyncio.sleep(host.sleep)

            if verbose:
                print('%s: waiting for hosts to terminate' % self.name)
            for sc in wait_hosts:
                await sc.wait()
            # wait for necessary hosts to terminate
        except:
            out.set_failed()
            traceback.print_exc()

        finally:
            out.set_end()

            # shut things back down
            if verbose:
                print('%s: cleaning up' % self.name)
            scs = []
            for _,sc in running:
                scs.append(sc.int_term_kill())
            await asyncio.wait(scs)

            for _,sc in running:
                await sc.wait()

            for sock in sockets:
                os.remove(sock)

            for sim,sc in running:
                out.add_sim(sim, sc)
        return out



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



def run_exp_local(exp, env, verbose=False):
    asyncio.run(exp.prepare(env, verbose=verbose))
    return asyncio.run(exp.run(env, verbose=verbose))
