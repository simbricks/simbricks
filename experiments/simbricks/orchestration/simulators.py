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

# Allow own class to be used as type for a method's argument
from __future__ import annotations

import math
import typing as tp

from simbricks.orchestration.experiment.experiment_environment import ExpEnv
from simbricks.orchestration.nodeconfig import NodeConfig


class Simulator(object):
    """Base class for all simulators."""

    def __init__(self):
        self.extra_deps = []
        self.name = ''

    def resreq_cores(self):
        """Number of cores required for this simulator."""
        return 1

    def resreq_mem(self):
        """Memory required for this simulator (in MB)."""
        return 64

    def full_name(self):
        """Full name of the simulator."""
        return ''

    # pylint: disable=unused-argument
    def prep_cmds(self, env: ExpEnv) -> tp.List[str]:
        """Commands to run to prepare simulator."""
        return []

    # pylint: disable=unused-argument
    def run_cmd(self, env: ExpEnv) -> tp.Optional[str]:
        """Command to run to execute simulator."""
        return None

    def dependencies(self) -> tp.List[Simulator]:
        """Other simulators this one depends on."""
        return []

    # Sockets to be cleaned up
    # pylint: disable=unused-argument
    def sockets_cleanup(self, env: ExpEnv):
        return []

    # sockets to wait for indicating the simulator is ready
    # pylint: disable=unused-argument
    def sockets_wait(self, env: ExpEnv):
        return []

    def start_delay(self):
        return 5

    def wait_terminate(self):
        return False


class PCIDevSim(Simulator):
    """Base class for PCIe device simulators."""

    def __init__(self):
        super().__init__()

        self.sync_mode = 0
        self.start_tick = 0
        self.sync_period = 500
        self.pci_latency = 500

    def full_name(self):
        return 'dev.' + self.name

    def is_nic(self):
        return False

    def sockets_cleanup(self, env):
        return [env.dev_pci_path(self), env.dev_shm_path(self)]

    def sockets_wait(self, env):
        return [env.dev_pci_path(self)]


class NICSim(PCIDevSim):
    """Base class for NIC simulators."""

    def __init__(self):
        super().__init__()

        self.network: tp.Optional[NetSim] = None
        self.mac: tp.Optional[str] = None
        self.eth_latency = 500
        """Ethernet latency in nanoseconds from this NIC to the network
        component."""

    def set_network(self, net: NetSim):
        """Connect this NIC to a network simulator."""
        self.network = net
        net.nics.append(self)

    def basic_args(self, env, extra=None):
        cmd = (
            f'{env.dev_pci_path(self)} {env.nic_eth_path(self)}'
            f' {env.dev_shm_path(self)} {self.sync_mode} {self.start_tick}'
            f' {self.sync_period} {self.pci_latency} {self.eth_latency}'
        )
        if self.mac is not None:
            cmd += ' ' + (''.join(reversed(self.mac.split(':'))))

        if extra is not None:
            cmd += ' ' + extra
        return cmd

    def basic_run_cmd(self, env, name, extra=None):
        cmd = f'{env.repodir}/sims/nic/{name} {self.basic_args(env, extra)}'
        return cmd

    def full_name(self):
        return 'nic.' + self.name

    def is_nic(self):
        return True

    def sockets_cleanup(self, env):
        return super().sockets_cleanup(env) + [env.nic_eth_path(self)]

    def sockets_wait(self, env):
        return super().sockets_wait(env) + [env.nic_eth_path(self)]


class NetSim(Simulator):
    """Base class for network simulators."""

    def __init__(self):
        super().__init__()

        self.opt = ''
        self.sync_mode = 0
        self.sync_period = 500
        """Synchronization period in nanoseconds from this network to connected
        components."""
        self.eth_latency = 500
        """Ethernet latency in nanoseconds from this network to connected
        components."""
        self.nics: list[NICSim] = []
        self.hosts_direct: list[HostSim] = []
        self.net_listen: list[NetSim] = []
        self.net_connect: list[NetSim] = []

    def full_name(self):
        return 'net.' + self.name

    def connect_network(self, net: NetSim):
        """Connect this network to the listening peer `net`"""
        net.net_listen.append(self)
        self.net_connect.append(net)

    def connect_sockets(self, env: ExpEnv) -> tp.List[tp.Tuple[Simulator, str]]:
        sockets = []
        for n in self.nics:
            sockets.append((n, env.nic_eth_path(n)))
        for n in self.net_connect:
            sockets.append((n, env.n2n_eth_path(n, self)))
        for h in self.hosts_direct:
            sockets.append((h, env.net2host_eth_path(self, h)))
        return sockets

    def listen_sockets(self, env: ExpEnv):
        listens = []
        for net in self.net_listen:
            listens.append((net, env.n2n_eth_path(self, net)))
        return listens

    def dependencies(self):
        return self.nics + self.net_connect + self.hosts_direct

    def sockets_cleanup(self, env: ExpEnv):
        return [s for (_, s) in self.listen_sockets(env)]

    def sockets_wait(self, env: ExpEnv):
        return [s for (_, s) in self.listen_sockets(env)]


# FIXME: Class hierarchy is broken here as an ugly hack
class MemDevSim(NICSim):
    """Base class for memory device simulators."""

    def __init__(self):
        super().__init__()

        self.name = ''
        self.sync_mode = 0
        self.start_tick = 0
        self.sync_period = 500
        self.mem_latency = 500
        self.addr = 0xe000000000000000
        self.size = 1024 * 1024 * 1024  # 1GB
        self.as_id = 0

    def full_name(self):
        return 'mem.' + self.name

    def sockets_cleanup(self, env):
        return [env.dev_mem_path(self), env.dev_shm_path(self)]

    def sockets_wait(self, env):
        return [env.dev_mem_path(self)]


class NetMemSim(NICSim):
    """Base class for netork memory simulators."""

    def __init__(self):
        super().__init__()

        self.name = ''
        self.sync_mode = 0
        self.start_tick = 0
        self.sync_period = 500
        self.eth_latency = 500
        self.addr = 0xe000000000000000
        self.size = 1024 * 1024 * 1024  # 1GB
        self.as_id = 0

    def full_name(self):
        return 'netmem.' + self.name

    def sockets_cleanup(self, env):
        return [env.nic_eth_path(self), env.dev_shm_path(self)]

    def sockets_wait(self, env):
        return [env.nic_eth_path(self)]


class HostSim(Simulator):
    """Base class for host simulators."""

    def __init__(self, node_config: NodeConfig):
        super().__init__()
        self.node_config = node_config
        """System configuration for this simulated host. """
        self.wait = False
        """
        `True` - Wait for this simulator to finish execution. `False` - Don't
        wait and instead shutdown the simulator as soon as all other awaited
        simulators have completed execution.
        """
        self.sleep = 0
        self.cpu_freq = '4GHz'

        self.sync_mode = 0
        self.sync_period = 500
        self.pci_latency = 500
        self.mem_latency = 500

        self.pcidevs: tp.List[PCIDevSim] = []
        self.net_directs: tp.List[NetSim] = []
        self.memdevs: tp.List[MemDevSim] = []

    @property
    def nics(self):
        return filter(lambda pcidev: pcidev.is_nic(), self.pcidevs)

    def full_name(self):
        return 'host.' + self.name

    def add_nic(self, dev: NICSim):
        """Add a NIC to this host."""
        self.add_pcidev(dev)

    def add_pcidev(self, dev: PCIDevSim):
        """Add a PCIe device to this host."""
        dev.name = self.name + '.' + dev.name
        self.pcidevs.append(dev)

    def add_memdev(self, dev: MemDevSim):
        dev.name = self.name + '.' + dev.name
        self.memdevs.append(dev)

    def add_netdirect(self, net: NetSim):
        """Add a direct connection to a network to this host."""
        net.hosts_direct.append(self)
        self.net_directs.append(net)

    def dependencies(self):
        deps = []
        for dev in self.pcidevs:
            deps.append(dev)
            if isinstance(dev, NICSim):
                deps.append(dev.network)
        for dev in self.memdevs:
            deps.append(dev)
        return deps

    def wait_terminate(self):
        return self.wait


class QemuHost(HostSim):
    """Qemu host simulator."""

    def __init__(self, node_config: NodeConfig):
        super().__init__(node_config)

        self.sync = False

    def resreq_cores(self):
        if self.sync:
            return 1
        else:
            return self.node_config.cores + 1

    def resreq_mem(self):
        return 8192

    def prep_cmds(self, env):
        return [
            f'{env.qemu_img_path} create -f qcow2 -o '
            f'backing_file="{env.hd_path(self.node_config.disk_image)}" '
            f'{env.hdcopy_path(self)}'
        ]

    def run_cmd(self, env):
        accel = ',accel=kvm:tcg' if not self.sync else ''
        if self.node_config.kcmd_append:
            kcmd_append = ' ' + self.node_config.kcmd_append
        else:
            kcmd_append = ''

        cmd = (
            f'{env.qemu_path} -machine q35{accel} -serial mon:stdio '
            '-cpu Skylake-Server -display none -nic none '
            f'-kernel {env.qemu_kernel_path} '
            f'-drive file={env.hdcopy_path(self)},if=ide,index=0,media=disk '
            f'-drive file={env.cfgtar_path(self)},if=ide,index=1,media=disk,'
            'driver=raw '
            '-append "earlyprintk=ttyS0 console=ttyS0 root=/dev/sda1 '
            f'init=/home/ubuntu/guestinit.sh rw{kcmd_append}" '
            f'-m {self.node_config.memory} -smp {self.node_config.cores} '
        )

        if self.sync:
            unit = self.cpu_freq[-3:]
            if unit.lower() == 'ghz':
                base = 0
            elif unit.lower() == 'mhz':
                base = 3
            else:
                raise ValueError('cpu frequency specified in unsupported unit')
            num = float(self.cpu_freq[:-3])
            shift = base - int(math.ceil(math.log(num, 2)))

            cmd += f' -icount shift={shift},sleep=off '

        for dev in self.pcidevs:
            cmd += f'-device simbricks-pci,socket={env.dev_pci_path(dev)}'
            if self.sync:
                cmd += ',sync=on'
                cmd += f',pci-latency={self.pci_latency}'
                cmd += f',sync-period={self.sync_period}'
            else:
                cmd += ',sync=off'
            cmd += ' '

        # qemu does not currently support net direct ports
        assert len(self.net_directs) == 0
        # qemu does not currently support mem device ports
        assert len(self.memdevs) == 0
        return cmd


class Gem5Host(HostSim):
    """Gem5 host simulator."""

    def __init__(self, node_config: NodeConfig):
        node_config.sim = 'gem5'
        super().__init__(node_config)
        self.cpu_type_cp = 'X86KvmCPU'
        self.cpu_type = 'TimingSimpleCPU'
        self.sys_clock = '1GHz'
        self.extra_main_args = []
        self.extra_config_args = []
        self.variant = 'fast'

    def resreq_cores(self):
        return 1

    def resreq_mem(self):
        return 4096

    def prep_cmds(self, env):
        return [f'mkdir -p {env.gem5_cpdir(self)}']

    def run_cmd(self, env):
        cpu_type = self.cpu_type
        if env.create_cp:
            cpu_type = self.cpu_type_cp

        cmd = f'{env.gem5_path(self.variant)} --outdir={env.gem5_outdir(self)} '
        cmd += ' '.join(self.extra_main_args)
        cmd += (
            f' {env.gem5_py_path} --caches --l2cache --l3cache '
            '--l1d_size=32kB --l1i_size=32kB --l2_size=2MB --l3_size=32MB '
            '--l1d_assoc=8 --l1i_assoc=8 --l2_assoc=4 --l3_assoc=16 '
            f'--cacheline_size=64 --cpu-clock={self.cpu_freq}'
            f' --sys-clock={self.sys_clock} '
            f'--checkpoint-dir={env.gem5_cpdir(self)} '
            f'--kernel={env.gem5_kernel_path} '
            f'--disk-image={env.hd_raw_path(self.node_config.disk_image)} '
            f'--disk-image={env.cfgtar_path(self)} '
            f'--cpu-type={cpu_type} --mem-size={self.node_config.memory}MB '
            f'--num-cpus={self.node_config.cores} '
            '--ddio-enabled --ddio-way-part=8 --mem-type=DDR4_2400_16x4 '
        )

        if self.node_config.kcmd_append:
            cmd += f'--command-line-append="{self.node_config.kcmd_append}" '

        if env.create_cp:
            cmd += '--max-checkpoints=1 '

        if env.restore_cp:
            cmd += '-r 1 '

        for dev in self.pcidevs:
            cmd += (
                f'--simbricks-pci=connect:{env.dev_pci_path(dev)}'
                f':latency={self.pci_latency}ns'
                f':sync_interval={self.sync_period}ns'
            )
            if cpu_type == 'TimingSimpleCPU':
                cmd += ':sync'
            cmd += ' '

        for dev in self.memdevs:
            cmd += (
                f'--simbricks-mem={dev.size}@{dev.addr}@{dev.as_id}@'
                f'connect:{env.dev_mem_path(dev)}'
                f':latency={self.mem_latency}ns'
                f':sync_interval={self.sync_period}ns'
            )
            if cpu_type == 'TimingSimpleCPU':
                cmd += ':sync'
            cmd += ' '

        for net in self.net_directs:
            cmd += (
                '--simbricks-eth-e1000=listen'
                f':{env.net2host_eth_path(net, self)}'
                f':{env.net2host_shm_path(net, self)}'
                f':latency={net.eth_latency}ns'
                f':sync_interval={net.sync_period}ns'
            )
            if cpu_type == 'TimingSimpleCPU':
                cmd += ':sync'
            cmd += ' '

        cmd += ' '.join(self.extra_config_args)
        return cmd


class SimicsHost(HostSim):
    """Simics host simulator."""

    def __init__(self, node_config: NodeConfig):
        super().__init__(node_config)
        node_config.sim = 'simics'

        self.cpu_class = 'x86-cooper-lake'
        """Simics CPU class. Can be obtained by running `list-classes substr =
        processor_` inside Simics."""
        self.cpu_freq = 4000  # TODO Don't hide attribute in super class
        """CPU frequency in MHz"""
        self.timing = False
        """Whether to run Simics in a more precise timing mode. This adds a
        cache model."""
        self.append_cmdline: tp.List[str] = []
        """Additional parameters to append on the command-line when invoking
        Simics."""
        self.interactive = False
        """Whether to launch Simics in interactive GUI mode. This is helpful for
        debugging, e.g. enabling log messages in the mid of the simulation."""
        self.debug_messages = False
        """Whether to enable debug messages of SimBricks adapter devices."""

    def resreq_cores(self):
        return 2

    def resreq_mem(self):
        return self.node_config.memory

    def run_cmd(self, env):
        if self.node_config.kcmd_append:
            raise RuntimeError(
                'Appending kernel command-line not yet implemented.'
            )

        if self.interactive and not env.create_cp:
            cmd = f'{env.simics_gui_path} -q '
        else:
            cmd = f'{env.simics_path} -q -batch-mode -werror '

        if env.restore_cp:
            # restore checkpoint
            cmd += f'-e \'read-configuration {env.simics_cpfile(self)}\' '
        else:
            # initialize simulated machine
            cmd += (
                '-e \'run-command-file '
                f'{env.simics_qsp_modern_core_path} '
                f'disk0_image = {env.hd_raw_path(self.node_config.disk_image)} '
                f'disk1_image = {env.cfgtar_path(self)} '
                f'cpu_comp_class = {self.cpu_class} '
                f'freq_mhz = {self.cpu_freq} '
                f'num_cores = {self.node_config.cores} '
                f'num_threads = {self.node_config.threads} '
                f'memory_megs = {self.node_config.memory}\' '
            )

        if env.create_cp:
            # stop simulation when encountering special checkpoint string on
            # serial console
            cmd += (
                '-e \'bp.console_string.break board.serconsole.con '
                '"ready to checkpoint"\' '
            )
            # run simulation
            cmd += '-e run '
            # create checkpoint
            cmd += f'-e \'write-configuration {env.simics_cpfile(self)}\' '
            return cmd

        if self.timing:
            # Add the cache model. Note that the caches aren't warmed up during
            # the boot process. The reason is that when later adding the memory
            # devices, we change the mapped memory. The cycle staller doesn't
            # like this and will SEGFAULT.
            #
            # The cache model doesn't store any memory contents and therefore
            # doesn't answer any memory transactions. It only inserts CPU stall
            # cycles on each cache level and can be queried for statistics as
            # well as which addresses are cached.
            #
            # Read penalties are based on https://www.7-cpu.com/cpu/Skylake.html
            cmd += (
                '-e \'new-cycle-staller name = cs0 '
                'stall-interval = 10000\' '
            )
            cmd += (
                '-e \'new-simple-cache-tool name = cachetool '
                'cycle-staller = cs0 -connect-all\' '
            )
            cmd += (
                '-e \'cachetool.add-l1i-cache name = l1i line-size = 64 '
                'sets = 64 ways = 8\' '
            )
            cmd += (
                '-e \'cachetool.add-l1d-cache name = l1d line-size = 64 '
                'sets = 64 ways = 8 -ip-read-prefetcher '
                'prefetch-additional = 1 read-penalty = 4\' '
            )
            cmd += (
                '-e \'cachetool.add-l2-cache name = l2 line-size = 64 '
                'sets = 8192 ways = 4 -prefetch-adjacent '
                'prefetch-additional = 4 read-penalty = 12\' '
            )
            cmd += (
                '-e \'cachetool.add-l3-cache name = l3 line-size = 64 '
                'sets = 32768 ways = 16 read-penalty = 42\' '
            )

        # Only simulate one cycle per CPU and then switch to the next. This is
        # necessary for the synchronization of the SimBricks adapter with all
        # the CPUs to work properly.
        cmd += '-e \'set-time-quantum 1\' '

        if self.memdevs:
            cmd += '-e \'load-module simbricks_mem_comp\' '

        for memdev in self.memdevs:
            cmd += (
                f'-e \'$mem = (new-simbricks-mem-comp '
                f'socket = "{env.dev_mem_path(memdev)}" '
                f'mem_latency = {self.mem_latency} '
                f'sync_period = {self.sync_period})\' '
            )
            cmd += (
                f'-e \'board.mb.dram_space.add-map $mem.simbricks_mem_dev '
                f'{memdev.addr:#x} {memdev.size:#x}\' '
            )
            if self.debug_messages:
                cmd += '-e \'$mem.log-level 3\' '

        for param in self.append_cmdline:
            cmd += f'{param} '

        # The simulation keeps running when the host powers off. A log message
        # indicates the event when the machine is powering off. We place a
        # breakpoint on that log message, which will terminate Simics due to the
        # use of `-batch-mode`.
        cmd += (
            '-e \'bp.log.break object=board.mb.sb.lpc.bank.acpi_io_regs '
            'substr="Sleep state is unimplemented" type=unimpl\' '
        )

        return cmd + '-e run'


class CorundumVerilatorNIC(NICSim):

    def __init__(self):
        super().__init__()
        self.clock_freq = 250  # MHz

    def resreq_mem(self):
        # this is a guess
        return 512

    def run_cmd(self, env):
        return self.basic_run_cmd(
            env, '/corundum/corundum_verilator', str(self.clock_freq)
        )


class CorundumBMNIC(NICSim):

    def run_cmd(self, env):
        return self.basic_run_cmd(env, '/corundum_bm/corundum_bm')


class I40eNIC(NICSim):

    def run_cmd(self, env):
        return self.basic_run_cmd(env, '/i40e_bm/i40e_bm')


class E1000NIC(NICSim):

    def __init__(self):
        super().__init__()
        self.debug = False

    def run_cmd(self, env):
        cmd = self.basic_run_cmd(env, '/e1000_gem5/e1000_gem5')
        if self.debug:
            cmd = 'env E1000_DEBUG=1 ' + cmd
        return cmd


class MultiSubNIC(NICSim):

    def __init__(self, mn):
        super().__init__()
        self.multinic = mn

    def full_name(self):
        return self.multinic.full_name() + '.' + self.name

    def dependencies(self):
        return super().dependencies() + [self.multinic]

    def start_delay(self):
        return 0


class I40eMultiNIC(Simulator):

    def __init__(self):
        super().__init__()
        self.subnics = []

    def create_subnic(self):
        sn = MultiSubNIC(self)
        self.subnics.append(sn)
        return sn

    def full_name(self):
        return 'multinic.' + self.name

    def run_cmd(self, env):
        args = ''
        first = True
        for sn in self.subnics:
            if not first:
                args += ' -- '
            first = False
            args += sn.basic_args(env)
        return f'{env.repodir}/sims/nic/i40e_bm/i40e_bm {args}'

    def sockets_cleanup(self, env):
        ss = []
        for sn in self.subnics:
            ss += sn.sockets_cleanup(env)
        return ss

    def sockets_wait(self, env):
        ss = []
        for sn in self.subnics:
            ss += sn.sockets_wait(env)
        return ss


class WireNet(NetSim):

    def run_cmd(self, env):
        connects = self.connect_sockets(env)
        assert len(connects) == 2
        cmd = (
            f'{env.repodir}/sims/net/wire/net_wire {connects[0][1]}'
            f' {connects[1][1]} {self.sync_mode} {self.sync_period}'
            f' {self.eth_latency}'
        )
        if len(env.pcap_file) > 0:
            cmd += ' ' + env.pcap_file
        return cmd


class SwitchNet(NetSim):

    def __init__(self):
        super().__init__()
        self.sync = True

    def run_cmd(self, env):
        cmd = env.repodir + '/sims/net/switch/net_switch'
        cmd += f' -S {self.sync_period} -E {self.eth_latency}'

        if not self.sync:
            cmd += ' -u'

        if len(env.pcap_file) > 0:
            cmd += ' -p ' + env.pcap_file
        for (_, n) in self.connect_sockets(env):
            cmd += ' -s ' + n
        for (_, n) in self.listen_sockets(env):
            cmd += ' -h ' + n
        return cmd

    def sockets_cleanup(self, env):
        # cleanup here will just have listening eth sockets, switch also creates
        # shm regions for each with a "-shm" suffix
        cleanup = []
        for s in super().sockets_cleanup(env):
            cleanup.append(s)
            cleanup.append(s + '-shm')
        return cleanup


class MemSwitchNet(NetSim):

    def __init__(self):
        super().__init__()
        self.sync = True
        """ AS_ID,VADDR_START,VADDR_END,MEMNODE_MAC,PHYS_START """
        self.mem_map = []

    def run_cmd(self, env):
        cmd = env.repodir + '/sims/mem/memswitch/memswitch'
        cmd += f' -S {self.sync_period} -E {self.eth_latency}'

        if not self.sync:
            cmd += ' -u'

        if len(env.pcap_file) > 0:
            cmd += ' -p ' + env.pcap_file
        for (_, n) in self.connect_sockets(env):
            cmd += ' -s ' + n
        for (_, n) in self.listen_sockets(env):
            cmd += ' -h ' + n
        for m in self.mem_map:
            cmd += ' -m ' + f' {m[0]},{m[1]},{m[2]},'
            cmd += (''.join(reversed(m[3].split(':'))))
            cmd += f',{m[4]}'
        return cmd

    def sockets_cleanup(self, env):
        # cleanup here will just have listening eth sockets, switch also creates
        # shm regions for each with a "-shm" suffix
        cleanup = []
        for s in super().sockets_cleanup(env):
            cleanup.append(s)
            cleanup.append(s + '-shm')
        return cleanup


class TofinoNet(NetSim):

    def __init__(self):
        super().__init__()
        self.tofino_log_path = '/tmp/model.ldjson'
        self.sync = True

    def run_cmd(self, env):
        cmd = f'{env.repodir}/sims/net/tofino/tofino'
        cmd += (
            f' -S {self.sync_period} -E {self.eth_latency}'
            f' -t {self.tofino_log_path}'
        )
        if not self.sync:
            cmd += ' -u'
        for (_, n) in self.connect_sockets(env):
            cmd += ' -s ' + n
        return cmd


class NS3DumbbellNet(NetSim):

    def run_cmd(self, env):
        ports = ''
        for (n, s) in self.connect_sockets(env):
            if 'server' in n.name:
                ports += f'--CosimPortLeft={s} '
            else:
                ports += f'--CosimPortRight={s} '

        cmd = (
            f'{env.repodir}/sims/external/ns-3'
            f'/cosim-run.sh cosim cosim-dumbbell-example {ports} {self.opt}'
        )
        print(cmd)

        return cmd


class NS3BridgeNet(NetSim):

    def run_cmd(self, env):
        ports = ''
        for (_, n) in self.connect_sockets(env):
            ports += '--CosimPort=' + n + ' '

        cmd = (
            f'{env.repodir}/sims/external/ns-3'
            f'/cosim-run.sh cosim cosim-bridge-example {ports} {self.opt}'
        )
        print(cmd)

        return cmd


class NS3SequencerNet(NetSim):

    def run_cmd(self, env):
        ports = ''
        for (n, s) in self.connect_sockets(env):
            if 'client' in n.name:
                ports += '--ClientPort=' + s + ' '
            elif 'replica' in n.name:
                ports += '--ServerPort=' + s + ' '
            elif 'sequencer' in n.name:
                ports += '--ServerPort=' + s + ' '
            else:
                raise KeyError('Wrong NIC type')
        cmd = (
            f'{env.repodir}/sims/external/ns-3'
            f'/cosim-run.sh sequencer sequencer-single-switch-example'
            f' {ports} {self.opt}'
        )
        return cmd


class FEMUDev(PCIDevSim):

    def run_cmd(self, env):
        cmd = (
            f'{env.repodir}/sims/external/femu/femu-simbricks'
            f' {env.dev_pci_path(self)} {env.dev_shm_path(self)}'
        )
        return cmd


class BasicMemDev(MemDevSim):

    def run_cmd(self, env):
        cmd = (
            f'{env.repodir}/sims/mem/basicmem/basicmem'
            f' {self.size} {self.addr} {self.as_id}'
            f' {env.dev_mem_path(self)} {env.dev_shm_path(self)}'
            f' {self.sync_mode} {self.start_tick} {self.sync_period}'
            f' {self.mem_latency}'
        )
        return cmd


class MemNIC(MemDevSim):

    def run_cmd(self, env):
        cmd = (
            f'{env.repodir}/sims/mem/memnic/memnic'
            f' {env.dev_mem_path(self)} {env.nic_eth_path(self)}'
            f' {env.dev_shm_path(self)}'
        )

        if self.mac is not None:
            cmd += ' ' + (''.join(reversed(self.mac.split(':'))))

        cmd += f' {self.sync_mode} {self.start_tick} {self.sync_period}'
        cmd += f' {self.mem_latency} {self.eth_latency}'

        return cmd

    def sockets_cleanup(self, env):
        return super().sockets_cleanup(env) + [env.nic_eth_path(self)]

    def sockets_wait(self, env):
        return super().sockets_wait(env) + [env.nic_eth_path(self)]


class NetMem(NetMemSim):

    def run_cmd(self, env):
        cmd = (
            f'{env.repodir}/sims/mem/netmem/netmem'
            f' {self.size} {self.addr} {self.as_id}'
            f' {env.nic_eth_path(self)}'
            f' {env.dev_shm_path(self)}'
        )
        if self.mac is not None:
            cmd += ' ' + (''.join(reversed(self.mac.split(':'))))

        cmd += f' {self.sync_mode} {self.start_tick} {self.sync_period}'
        cmd += f' {self.eth_latency}'

        return cmd
