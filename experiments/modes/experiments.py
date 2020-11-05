import os
import asyncio
import modes.exectools as exectools
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

    def add_host(self, sim):
        self.hosts.append(sim)

    def add_nic(self, sim):
        self.nics.append(sim)

    def add_network(self, sim):
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
                        shlex.split(nic.run_cmd(env)), verbose=verbose)
                await sc.start()
                running.append((nic, sc))

                sockets.append(env.nic_pci_path(nic))
                sockets.append(env.nic_eth_path(nic))
                sockets.append(env.nic_shm_path(nic))

            if verbose:
                print('%s: waiting for sockets' % self.name)

            for s in sockets:
                await exectools.await_file(s, verbose=verbose)

            # start networks
            for net in self.networks:
                if verbose:
                    print('start Net:', net.run_cmd(env))

                sc = exectools.SimpleComponent(net.full_name(),
                        shlex.split(net.run_cmd(env)), verbose=verbose)
                await sc.start()
                running.append((net, sc))

            # start hosts
            wait_hosts = []
            for host in self.hosts:
                if verbose:
                    print('start Host:', host.run_cmd(env))

                sc = exectools.SimpleComponent(host.full_name(),
                        shlex.split(host.run_cmd(env)), verbose=verbose)
                await sc.start()
                running.append((host,sc))

                if host.wait:
                    wait_hosts.append(sc)

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
    def __init__(self, repo_path, workdir):
        self.repodir = os.path.abspath(repo_path)
        self.workdir = os.path.abspath(workdir)
        self.qemu_img_path = self.repodir + '/qemu/qemu-img'
        self.qemu_path = self.repodir + '/qemu/x86_64-softmmu/qemu-system-x86_64'
        self.qemu_kernel_path = self.repodir + '/images/bzImage'

    def hdcopy_path(self, sim):
        return '%s/hdcopy.%s.%d' % (self.workdir, sim.name, id(sim))

    def hd_path(self, hd_name):
        return '%s/images/output-%s/%s' % (self.repodir, hd_name, hd_name)

    def cfgtar_path(self, sim):
        return '%s/cfg.%s.%d.tar' % (self.workdir, sim.name, id(sim))

    def nic_pci_path(self, sim):
        return '%s/nic.pci.%s.%d' % (self.workdir, sim.name, id(sim))

    def nic_eth_path(self, sim):
        return '%s/nic.eth.%s.%d' % (self.workdir, sim.name, id(sim))

    def nic_shm_path(self, sim):
        return '%s/nic.shm.%s.%d' % (self.workdir, sim.name, id(sim))

class ExpOutput(object):
    def __init__(self, exp):
        self.exp_name = exp.name
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
