import io
import typing as tp
import itertools

class System():
    """ Defines System configuration of the whole simulation """

    def __init__(self) -> None:
        self.hosts: tp.List[Host] = []
        self.nics: tp.List[NIC] = []
        self.switches: tp.List[Switch] = []
        self.pci_channels: tp.List[PCI] = []
        self.eth_channels: tp.List[Eth] = []

class Channel():
    def __init__(self) -> None:
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

    
class Host():
    id_iter = itertools.count()

    def __init__(self, sys) -> None:
        self.id = next(self.id_iter)
        sys.hosts.append(self)
        self.sync = True
        self.pci_channel: PCI = None
        self.nics: tp.List[NIC] = []
        self.nic_driver = 'i40e'

        # HostSim & NodeConfig parameters
        self.cpu_freq = '3GHz'
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
        self.tcp_congestion_control = 'bic'
        """TCP Congestion Control algorithm to use."""
        self.app: tp.Optional[AppConfig] = None
        """Application to run on simulated host."""


"""
Pci device NIC
It has both pci and eth channel
"""
class NIC():
    id_iter = itertools.count()
    def __init__(self, sys) -> None:
        self.id = next(self.id_iter)
        sys.nics.append(self)
        self.sync = True
        self.pci_channel: PCI = None
        self.eth_channel: Eth = None
        self.frequency = '1Ghz'
        self.mac: tp.Optional[str] = None
        self.host: tp.List[Host] = []
        self.net = [] # NIC or NetDev connected through eth channel
        

class i40eNIC(NIC):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.type = 'i40e'


"""
Network device
It only has eth channel
"""
class NetDev():
    id_iter = itertools.count()
    def __init__(self) -> None:
        self.id = next(self.id_iter)
        self.switch: Switch = None
        self.sync = True
        self.eth_channel: Eth = None
        self.mac: tp.Optional[str] = None
        self.ip: tp.Optional[str] = None
        self.net = [] # NIC or NetDev connected through eth channel

class Switch():
    id_iter = itertools.count()
    def __init__(self, sys) -> None:
        self.id = next(self.id_iter)
        sys.switches.append(self)
        self.sync = True
        self.netdevs : tp.List[NetDev] = []
    
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


