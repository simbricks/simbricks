import io
import typing as tp
import tarfile
import itertools

class System():
    """ Defines System configuration of the whole simulation """

    def __init__(self) -> None:
        self.hosts: tp.List[Host] = []
        self.nics: tp.List[NIC] = []
        self.switches: tp.List[Switch] = []
        self.pci_channels: tp.List[PCI] = []
        self.eth_channels: tp.List[Eth] = []

class SimObject():
    def __init__(self) -> None:
        self.sync_period = 500 #nano second

class Channel(SimObject):
    def __init__(self) -> None:
        super().__init__()
        self.latency = 500 # nano second

    def install(self, end_point0, end_point1) -> None:
        return

class PCI(Channel):
    def __init__(self, sys) -> None:
        super().__init__()
        self.end_point_host = None
        self.end_point_dev = None
        sys.pci_channels.append(self)
    def install(self, host, dev) -> None:
        self.end_point_host = host
        self.end_point_dev = dev

        host.nics.append(dev)
        host.pci_channel = self
        dev.host.append(host)
        dev.pci_channel = self

class Eth(Channel):
    def __init__(self, sys) -> None:
        super().__init__()
        self.end_point_netdev0 = None
        self.end_point_netdev1 = None
        sys.eth_channels.append(self)

    def install(self, netdev0, netdev1):
        self.end_point_netdev0 = netdev0
        self.end_point_netdev1 = netdev1

        netdev0.net.append(netdev1)
        netdev0.eth_channel = self
        netdev1.net.append(netdev0)
        netdev1.eth_channel = self

    
class Host(SimObject):
    id_iter = itertools.count()

    def __init__(self, sys) -> None:
        super().__init__()
        self.id = next(self.id_iter)
        sys.hosts.append(self)

        self.pci_channel: PCI = None
        self.nics: tp.List[NIC] = []
        self.sim = None
        self.nic_driver = ['i40e']

        self.sync = True
        """Synchronization mode. False is running unsynchronized, True synchronized."""
        self.cpu_freq = '3GHz'
        """Simulated host frequency"""
        self.ip = '10.0.0.1'
        """IP address."""
        self.prefix = 24
        """IP prefix."""
        self.cores = 1
        """Number of CPU cores."""
        self.threads = 1
        """Number of threads per CPU core."""
        self.memory = 512
        """Amount of system memory in MB."""
        self.disk_image = 'base'
        """Name of disk image to use."""
        self.mtu = 1500
        """Networking MTU."""
        self.sys_clock = '1GHz'
        """system bus clock"""
        self.tcp_congestion_control = 'bic'
        """TCP Congestion Control algorithm to use."""
        self.app: tp.Optional[AppConfig] = None
        """Application to run on simulated host."""
        self.kcmd_append = ''
        """String to be appended to kernel command line."""
        self.nockp = 0
        """Do not create a checkpoint in Gem5."""

    
    def config_str(self) -> str:
        import simbricks.splitsim.impl as impl
        if type(self.sim) is impl.Gem5Sim :
            cp_es = [] if self.nockp else ['m5 checkpoint']
            exit_es = ['m5 exit']
        else:
            cp_es = ['echo ready to checkpoint']
            exit_es = ['poweroff -f']

        es = self.prepare_pre_cp() + self.app.prepare_pre_cp(self) + cp_es + \
            self.prepare_post_cp() + self.app.prepare_post_cp(self) + \
            self.run_cmds() + self.cleanup_cmds() + exit_es
        return '\n'.join(es)

    def make_tar(self, path: str) -> None:
        with tarfile.open(path, 'w:') as tar:
            # add main run script
            cfg_i = tarfile.TarInfo('guest/run.sh')
            cfg_i.mode = 0o777
            cfg_f = self.strfile(self.config_str())
            cfg_f.seek(0, io.SEEK_END)
            cfg_i.size = cfg_f.tell()
            cfg_f.seek(0, io.SEEK_SET)
            tar.addfile(tarinfo=cfg_i, fileobj=cfg_f)
            cfg_f.close()

            # add additional config files
            for (n, f) in self.config_files().items():
                f_i = tarfile.TarInfo('guest/' + n)
                f_i.mode = 0o777
                f.seek(0, io.SEEK_END)
                f_i.size = f.tell()
                f.seek(0, io.SEEK_SET)
                tar.addfile(tarinfo=f_i, fileobj=f)
                f.close()


    def run_cmds(self) -> tp.List[str]:
        """Commands to run on node."""
        return self.app.run_cmds(self)

    def cleanup_cmds(self) -> tp.List[str]:
        """Commands to run to cleanup node."""
        return []
    
    def config_files(self) -> tp.Dict[str, tp.IO]:
        """
        Additional files to put inside the node, which are mounted under
        `/tmp/guest/`.

        Specified in the following format: `filename_inside_node`:
        `IO_handle_of_file`
        """
        return self.app.config_files()
    
    def prepare_pre_cp(self) -> tp.List[str]:
        """Commands to run to prepare node before checkpointing."""
        return [
            'set -x',
            'export HOME=/root',
            'export LANG=en_US',
            'export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:' + \
                '/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"'
        ]

    def prepare_post_cp(self) -> tp.List[str]:
        """Commands to run to prepare node after checkpoint restore."""
        return []
    

    def strfile(self, s: str) -> io.BytesIO:
        """
        Helper function to convert a string to an IO handle for usage in
        `config_files()`.

        Using this, you can create a file with the string as its content on the
        simulated node.
        """
        return io.BytesIO(bytes(s, encoding='UTF-8'))
    

class LinuxHost(Host):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.ifname = 'eth0'
        self.force_mac_addr: tp.Optional[str] = None
    

    def prepare_post_cp(self) -> tp.List[str]:
        l = []
        for d in self.nic_driver:
            if d[0] == '/':
                l.append('insmod ' + d)
            else:
                l.append('modprobe ' + d)
        if self.force_mac_addr:
            l.append(
                'ip link set dev ' + self.ifname + ' address ' +
                self.force_mac_addr
            )
        l.append('ip link set dev ' + self.ifname + ' up')
        l.append(f'ip addr add {self.ip}/{self.prefix} dev {self.ifname}')
        return super().prepare_post_cp() + l

"""
Pci device NIC
It has both pci and eth channel
"""
class NIC(SimObject):
    id_iter = itertools.count()
    def __init__(self, sys) -> None:
        super().__init__()
        self.id = next(self.id_iter)
        sys.nics.append(self)
        self.sync = True
        self.pci_channel: PCI = None
        self.eth_channel: Eth = None
        self.frequency = '1Ghz'
        self.mac: tp.Optional[str] = None
        self.host: tp.List[Host] = []
        self.net = [] # NIC or NetDev connected through eth channel
        self.sim = None


class i40eNIC(NIC):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.type = 'i40e'


"""
Network device
It only has eth channel
"""
class NetDev(SimObject):
    id_iter = itertools.count()
    def __init__(self) -> None:
        super().__init__()
        self.id = next(self.id_iter)
        self.switch: Switch = None
        self.sync = True
        self.eth_channel: Eth = None
        self.mac: tp.Optional[str] = None
        self.ip: tp.Optional[str] = None
        self.net = [] # NIC or NetDev connected through eth channel
        self.sim = None


class Switch(SimObject):
    id_iter = itertools.count()
    def __init__(self, sys) -> None:
        super().__init__()
        self.id = next(self.id_iter)
        sys.switches.append(self)
        self.sync = True
        # these two: set it when install the channel
        self.sync_period = 500 # ns second
        self.eth_latency = 500 # ns second
        ###
        self.netdevs : tp.List[NetDev] = []
        self.sim = None

    
    def install_netdev(self, netdev: NetDev):
        self.netdevs.append(netdev)
        netdev.switch = self
    
class AppConfig():
    """Defines the application to run on a node or host."""
    """ Commands for detailed Host"""
    def run_cmds(self, node: Host) -> tp.List[str]:
        """Commands to run for this application."""
        return []

    def prepare_pre_cp(self, node: Host) -> tp.List[str]:
        """Commands to run to prepare this application before checkpointing."""
        return []

    def prepare_post_cp(self, node: Host) -> tp.List[str]:
        """Commands to run to prepare this application after the checkpoint is
        restored."""
        return []

    def config_files(self) -> tp.Dict[str, tp.IO]:
        """
        Additional files to put inside the node, which are mounted under
        `/tmp/guest/`.

        Specified in the following format: `filename_inside_node`:
        `IO_handle_of_file`
        """
        return {}

    def strfile(self, s: str) -> io.BytesIO:
        """
        Helper function to convert a string to an IO handle for usage in
        `config_files()`.

        Using this, you can create a file with the string as its content on the
        simulated node.
        """
        return io.BytesIO(bytes(s, encoding='UTF-8'))

    """ Commands for dummy Host (e.g. app names for ns-3)"""

class PingClient(AppConfig):

    def __init__(self, server_ip: str = '192.168.64.1') -> None:
        super().__init__()
        self.server_ip = server_ip
    
    def run_cmds(self, node: Host) -> tp.List[str]:
        return [f'ping {self.server_ip} -c 10']

    ### add commands for dummy Hosts here


class Sleep(AppConfig):

    def __init__(self, server_ip: str = '192.168.64.2') -> None:
        super().__init__()
        self.server_ip = server_ip
    
    def run_cmds(self, node: Host) -> tp.List[str]:
        return ['sleep 10']