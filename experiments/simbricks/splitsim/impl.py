import io
import typing as tp
import itertools
import simbricks.splitsim.specification as spec
import simbricks.orchestration.experiments as exp
from simbricks.orchestration.experiment.experiment_environment_new import ExpEnv

class Simulator(object):
    """Base class for all simulators."""

    def __init__(self) -> None:
        self.extra_deps: tp.List[Simulator] = []
        self.name = ''

    def resreq_cores(self) -> int:
        """
        Number of cores this simulator requires during execution.

        This is used for scheduling multiple runs and experiments.
        """
        return 1

    def resreq_mem(self) -> int:
        """
        Number of memory in MB this simulator requires during execution.

        This is used for scheduling multiple runs and experiments.
        """
        return 64

    def full_name(self) -> str:
        """Full name of the simulator."""
        return ''

    # pylint: disable=unused-argument
    def prep_cmds(self, env: ExpEnv) -> tp.List[str]:
        """Commands to prepare execution of this simulator."""
        return []

    # pylint: disable=unused-argument
    def run_cmd(self, env: ExpEnv) -> tp.Optional[str]:
        """Command to execute this simulator."""
        return None

    def dependencies(self):
        """Other simulators to execute before this one."""
        return []

    # Sockets to be cleaned up
    # pylint: disable=unused-argument
    def sockets_cleanup(self, env: ExpEnv) -> tp.List[str]:
        return []

    # sockets to wait for indicating the simulator is ready
    # pylint: disable=unused-argument
    def sockets_wait(self, env: ExpEnv) -> tp.List[str]:
        return []

    def start_delay(self) -> int:
        return 5

    def wait_terminate(self) -> bool:
        return False


class Gem5Sim(Simulator):

    def __init__(self, e: exp.Experiment):
        super().__init__()
        self.experiment = e
        self.hosts: tp.List[spec.Host] = []
        self.nics: tp.List[spec.NIC] = []

        # move it to add
        self.sync_period = 500
        """Period in nanoseconds of sending synchronization messages from this
        device to connected components."""
        self.pci_latency = 500

        self.name = ''

        self.cpu_type_cp = 'X86KvmCPU'
        self.cpu_type = 'TimingSimpleCPU'
        self.extra_main_args = []
        self.extra_config_args = []
        self.variant = 'fast'
        self.modify_checkpoint_tick = True
        self.wait = True
    
    def full_name(self) -> str:
        return 'host.' + self.name

    def resreq_cores(self) -> int:
        return 1

    def resreq_mem(self) -> int:
        return 4096

    def dependencies(self) -> tp.List[Simulator]:
        deps = []
        for h in self.hosts:
            for dev in h.nics:
                deps.append(dev.sim)
        return deps
    
    def add(self, host: spec.Host):
        self.hosts.append(host)
        self.nics = host.nics
        host.sim = self
        self.name = f'{self.hosts[0].id}'

        self.experiment.add_host(self)


    def prep_cmds(self, env: ExpEnv) -> tp.List[str]:
        cmds = [f'mkdir -p {env.gem5_cpdir(self)}']
        if env.restore_cp and self.modify_checkpoint_tick:
            cmds.append(
                f'python3 {env.utilsdir}/modify_gem5_cp_tick.py --tick 0 '
                f'--cpdir {env.gem5_cpdir(self)}'
            )
        return cmds
    

    def run_cmd(self, env: ExpEnv) -> str:
        cpu_type = self.cpu_type
        if env.create_cp:
            cpu_type = self.cpu_type_cp

        cmd = f'{env.gem5_path(self.variant)} --outdir={env.gem5_outdir(self)} '
        cmd += ' '.join(self.extra_main_args)
        cmd += (
            f' {env.gem5_py_path} --caches --l2cache '
            '--l1d_size=32kB --l1i_size=32kB --l2_size=32MB '
            '--l1d_assoc=8 --l1i_assoc=8 --l2_assoc=16 '
            f'--cacheline_size=64 --cpu-clock={self.hosts[0].cpu_freq}'
            f' --sys-clock={self.hosts[0].sys_clock} '
            f'--checkpoint-dir={env.gem5_cpdir(self)} '
            f'--kernel={env.gem5_kernel_path} '
            f'--disk-image={env.hd_raw_path(self.hosts[0].disk_image)} '
            f'--disk-image={env.cfgtar_path(self)} '
            f'--cpu-type={cpu_type} --mem-size={self.hosts[0].memory}MB '
            f'--num-cpus={self.hosts[0].cores} '
            '--mem-type=DDR4_2400_16x4 '
        )


        for dev in self.nics:
            cmd += (
                f'--simbricks-pci=connect:{env.dev_pci_path(dev.sim)}'
                f':latency={self.pci_latency}ns'
                f':sync_interval={self.sync_period}ns'
            )
            if cpu_type == 'TimingSimpleCPU':
                cmd += ':sync'
            cmd += ' '

        return cmd
    

    def wait_terminate(self) -> bool:
        return self.wait


class I40eNicSim(Simulator):

    def __init__(self, e: exp.Experiment):
        super().__init__()
        self.experiment = e
        self.nics: tp.List[spec.i40eNIC] = []
        self.start_tick = 0

    
    def add(self, nic: spec.i40eNIC):
        self.nics.append(nic)
        nic.sim = self
        self.experiment.add_nic(self)
        self.name = f'{nic.id}'

    def basic_args(self, env: ExpEnv, extra: tp.Optional[str] = None) -> str:
        cmd = (
            f'{env.dev_pci_path(self)} {env.nic_eth_path(self)}'
            f' {env.dev_shm_path(self)} {self.nics[0].sync} {self.start_tick}'
            f' {self.nics[0].eth_channel.sync_period} {self.nics[0].pci_channel.latency} {self.nics[0].eth_channel.latency}'
        )
        if self.nics[0].mac is not None:
            cmd += ' ' + (''.join(reversed(self.nics[0].mac.split(':'))))

        if extra is not None:
            cmd += ' ' + extra
        return cmd

    def basic_run_cmd(
        self, env: ExpEnv, name: str, extra: tp.Optional[str] = None
    ) -> str:
        cmd = f'{env.repodir}/sims/nic/{name} {self.basic_args(env, extra)}'
        return cmd

    def full_name(self) -> str:
        return 'nic.' + self.name

    def is_nic(self) -> bool:
        return True

    def sockets_cleanup(self, env: ExpEnv) -> tp.List[str]:
        return super().sockets_cleanup(env) + [env.nic_eth_path(self)]

    def sockets_wait(self, env: ExpEnv) -> tp.List[str]:
        return super().sockets_wait(env) + [env.nic_eth_path(self)]
    
    def run_cmd(self, env: ExpEnv) -> str:
        return self.basic_run_cmd(env, '/i40e_bm/i40e_bm')

    

class SwitchBMSim(Simulator):

    def __init__(self, e: exp.Experiment):
        super().__init__()
        self.experiment = e
        self.switches: tp.List[spec.Switch] = []
        self.nicSim: tp.List[I40eNicSim] = []
        self.wait = False

    def full_name(self) -> str:
        return 'net.' + self.name
    
    
    def add(self, switch: spec.Switch):
        self.switches.append(switch)
        switch.sim = self
        self.experiment.add_network(self)

        for s in self.switches:
            for n in s.netdevs:
                 self.nicSim.append(n.net[0].sim)

    def connect_sockets(self, env: ExpEnv) -> tp.List[tp.Tuple[Simulator, str]]:
        sockets = []
        for n in self.nicSim:
            sockets.append((n, env.nic_eth_path(n)))
        return sockets    

    def dependencies(self) -> tp.List[Simulator]:
        deps = []
        for s in self.switches:
            for n in s.netdevs:
                deps.append(n.net[0].sim)
        return deps
    
    def sockets_cleanup(self, env: ExpEnv) -> tp.List[str]:
        pass

    def sockets_wait(self, env: ExpEnv) -> tp.List[str]:
        pass

    def wait_terminate(self) -> bool:
        return self.wait

    def init_network(self) -> None:
        pass

    def sockets_cleanup(self, env: ExpEnv) -> tp.List[str]:
        cleanup = []
        return cleanup

    def run_cmd(self, env: ExpEnv) -> str:
        cmd = env.repodir + '/sims/net/switch/net_switch'
        cmd += f' -S {self.switches[0].sync_period} -E {self.switches[0].eth_latency}'

        if not self.switches[0].sync:
            cmd += ' -u'

        if len(env.pcap_file) > 0:
            cmd += ' -p ' + env.pcap_file
        for (_, n) in self.connect_sockets(env):
            cmd += ' -s ' + n
        # for (_, n) in self.listen_sockets(env):
        #     cmd += ' -h ' + n
        return cmd