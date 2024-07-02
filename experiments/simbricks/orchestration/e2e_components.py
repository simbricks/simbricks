# Copyright 2023 Max Planck Institute for Software Systems, and
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

import typing as tp
from abc import ABC, abstractmethod
from enum import Enum


class CongestionControl(Enum):
    RENO = ('ns3::TcpLinuxReno', 'reno')
    WESTWOOD = ('ns3::TcpWestwoodPlus', 'westwood')
    BIC = ('ns3::TcpBic', 'bic')
    CUBIC = ('ns3::TcpCubic', 'cubic')
    HTCP = ('ns3::TcpHtcp', 'htcp')
    HYBLA = ('ns3::TcpHybla', 'hybla')
    VEGAS = ('ns3::TcpVegas', 'vegas')
    NV = ('', 'nv')
    SCALABLE = ('ns3::TcpScalable', 'scalable')
    LP = ('ns3::TcpLp', 'lp')
    VENO = ('ns3::TcpVeno', 'veno')
    YEAH = ('ns3::TcpYeah', 'yeah')
    ILLINOIS = ('ns3::TcpIllinois', 'illinois')
    DCTCP = ('ns3::TcpDctcp', 'dctcp')
    CDG = ('', 'cdg')
    BBR = ('ns3::TcpBbr', 'bbr')
    HIGHSPEED = ('ns3::TcpHighSpeed', 'highspeed')

    def __init__(self, ns3_str, gem5_str):
        self.ns3_str = ns3_str
        self.gem5_str = gem5_str

    def __str__(self):
        return self.name.lower()

    @property
    def ns3(self):
        if self.ns3_str == '':
            raise AttributeError(
                f'There is no ns3 implementation for '
                f'{self.name} available'
            )
        return self.ns3_str

    @property
    def gem5(self):
        return self.gem5_str


class SimbricksAdapterType(Enum):
    NIC = 0
    NETWORK = 1
    HOST = 2


class SimbricksSyncMode(Enum):
    SYNC_DISABLED = 0
    SYNC_OPTIONAL = 1
    SYNC_REQUIRED = 2


class Ns3LoggingLevel(Enum):
    ERROR = 'error'
    LEVEL_ERROR = 'level_error'
    WARN = 'warn'
    LEVEL_WARN = 'level_warn'
    DEBUG = 'debug'
    LEVEL_DEBUG = 'level_debug'
    INFO = 'info'
    LEVEL_INFO = 'level_info'
    FUNCTION = 'function'
    LEVEL_FUNCTION = 'level_function'
    LOGIC = 'logic'
    LEVEL_LOGIC = 'level_logic'
    ALL = 'all'
    LEVEL_ALL = 'level_all'
    PREFIX_FUNC = 'prefix_func'
    PREFIX_TIME = 'prefix_time'
    PREFIX_NODE = 'prefix_node'
    PREFIX_LEVEL = 'prefix_level'
    PREFIX_ALL = 'prefix_all'


class E2EBase(ABC):

    def __init__(self) -> None:
        self.category: str
        self.mapping: tp.Dict[str, str] = {}
        self.components: tp.List[E2EComponent] = []

    def ns3_config(self) -> str:
        config_list = []
        for key, value in self.mapping.items():
            if value == '':
                continue
            config_list.append(f'{key}:{value}')
        config = ';'.join(config_list)

        child_configs = ' '.join([
            child.ns3_config() for child in self.components
        ])

        return f'--{self.category}="{config}" {child_configs}'

    @abstractmethod
    def add_component(self, component: E2EComponent) -> None:
        pass


class E2EGlobalConfig(E2EBase):

    def __init__(self) -> None:
        super().__init__()
        self.category = 'Global'
        self.stop_time = ''
        self.mac_start = 0

    def ns3_config(self) -> str:
        self.mapping.update({
            'StopTime': self.stop_time, 'MACStart': str(self.mac_start)
        })
        return super().ns3_config()

    def add_component(self, component: E2EComponent) -> None:
        raise AttributeError("Can't add a component to the global config")


class E2ENs3Logging(E2EBase):

    def __init__(self) -> None:
        super().__init__()
        self.category = 'Logging'
        self.logging: tp.Dict[str, tp.List[Ns3LoggingLevel]] = {}

    def ns3_config(self) -> str:
        for component, levels in self.logging.items():
            levels_str = '|'.join([level.value for level in levels])
            self.mapping.update([(component, levels_str)])
        return super().ns3_config()

    def add_component(self, component: E2EComponent) -> None:
        raise AttributeError("Can't add a component to the global config")

    def add_logging(self, component: str, level: Ns3LoggingLevel):
        if component in self.logging:
            self.logging[component].append(level)
        else:
            self.logging[component] = [level]


class E2EComponent(E2EBase):

    def __init__(self, idd: str) -> None:
        super().__init__()
        self.name = idd
        self.id = idd
        self.has_path = False
        self.type = ''

    def ns3_config(self) -> str:
        if self.id == '' or self.type == '':
            raise AttributeError('Id or Type cannot be empty')
        self.mapping.update({'Id': self.id, 'Type': self.type})

        return super().ns3_config()

    def add_component(self, component: E2EComponent) -> None:
        self.components.append(component)

    def resolve_paths(self) -> None:
        self.has_path = True
        for component in self.components:
            path = f'{self.id}/{component.id}'
            if component.has_path:
                raise AttributeError(
                    f'Component {component.id} was already '
                    f'added to another component (while trying '
                    f'to assign {path}).'
                )
            component.id = path
            component.resolve_paths()


class E2ETopologyNode(E2EComponent):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.category = 'TopologyNode'
        self.network = None


class E2ESwitchNode(E2ETopologyNode):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.type = 'Switch'
        self.mtu = ''

    def ns3_config(self) -> str:
        self.mapping.update({
            'Mtu': self.mtu,
        })
        return super().ns3_config()


class E2ETopologyChannel(E2EComponent):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.category = 'TopologyChannel'


class E2ESimpleChannel(E2ETopologyChannel):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.type = 'Simple'
        self.data_rate = ''
        self.queue_type = 'ns3::DropTailQueue'
        self.queue_size = ''
        self.channel_type = 'ns3::SimpleChannel'
        self.delay = ''
        self.left_node: E2ETopologyNode
        self.right_node: E2ETopologyNode

    def ns3_config(self) -> str:
        if self.left_node is None or self.right_node is None:
            raise AttributeError(f'Not all nodes for channel {self.id} given')
        self.mapping.update({
            'Device-DataRate': self.data_rate,
            'QueueType': self.queue_type,
            'Queue-MaxSize': self.queue_size,
            'ChannelType': self.channel_type,
            'Channel-Delay': self.delay,
            'LeftNode': self.left_node.id,
            'RightNode': self.right_node.id,
        })
        return super().ns3_config()

    def add_device_attr(self, key: str, value: str) -> None:
        if not key.startswith('Device-'):
            key = f'Device-{key}'
        self.mapping.update({key: value})

    def add_queue_attr(self, key: str, value: str) -> None:
        if not key.startswith('Queue-'):
            key = f'Queue-{key}'
        self.mapping.update({key: value})

    def add_channel_attr(self, key: str, value: str) -> None:
        if not key.startswith('Channel-'):
            key = f'Channel-{key}'
        self.mapping.update({key: value})


class E2ENetwork(E2EComponent):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.category = 'Network'
        self.peer = None

    def set_peer(self, peer: E2ENetwork):
        self.peer = peer
        peer.peer = self


class E2ENetworkSimbricks(E2ENetwork):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.type = 'Simbricks'
        self.adapter_type = SimbricksAdapterType.NETWORK
        self.unix_socket = ''
        self.sync_delay = ''
        self.poll_delay = ''
        self.eth_latency = ''
        self.listen: tp.Optional[bool] = None
        self.shm_path = ''
        self.sync: SimbricksSyncMode = SimbricksSyncMode.SYNC_OPTIONAL

        self.simbricks_component = None

    def ns3_config(self) -> str:
        if self.listen is None:
            raise AttributeError(
                f'Listen mode not specified for simbricks adapter {self.id}'
            )
        self.mapping.update({
            'UnixSocket': self.unix_socket,
            'SyncDelay': self.sync_delay,
            'PollDelay': self.poll_delay,
            'EthLatency': self.eth_latency,
            'Listen': 'true' if self.listen else 'false',
            'ShmPath': self.shm_path,
            'Sync': '' if self.sync is None else f'{self.sync.value}',
        })
        return super().ns3_config()


class E2EHost(E2EComponent):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.category = 'Host'


class E2ESimbricksHost(E2EHost):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.type = 'Simbricks'
        self.adapter_type = SimbricksAdapterType.NIC
        self.unix_socket = ''
        self.sync_delay = ''
        self.poll_delay = ''
        self.eth_latency = ''
        self.sync: SimbricksSyncMode = SimbricksSyncMode.SYNC_OPTIONAL

        self.simbricks_component = None

    def ns3_config(self) -> str:
        self.mapping.update({
            'UnixSocket': self.unix_socket,
            'SyncDelay': self.sync_delay,
            'PollDelay': self.poll_delay,
            'EthLatency': self.eth_latency,
            'Sync': '' if self.sync is None else f'{self.sync.value}',
        })
        return super().ns3_config()


class E2ESimpleNs3Host(E2EHost):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.type = 'SimpleNs3'
        self.data_rate = ''
        self.queue_type = 'ns3::DropTailQueue'
        self.queue_size = ''
        self.channel_type = 'ns3::SimpleChannel'
        self.delay = ''
        self.congestion_control: CongestionControl = None
        self.ip = ''

    def ns3_config(self) -> str:
        if self.congestion_control is None:
            cc = ''
        else:
            cc = self.congestion_control.ns3
        self.mapping.update({
            'Device-DataRate': self.data_rate,
            'QueueType': self.queue_type,
            'Queue-MaxSize': self.queue_size,
            'ChannelType': self.channel_type,
            'Channel-Delay': self.delay,
            'CongestionControl': cc,
            'Ip': self.ip,
        })
        return super().ns3_config()

    def add_device_attr(self, key: str, value: str) -> None:
        if not key.startswith('Device-'):
            key = f'Device-{key}'
        self.mapping.update({key: value})

    def add_queue_attr(self, key: str, value: str) -> None:
        if not key.startswith('Queue-'):
            key = f'Queue-{key}'
        self.mapping.update({key: value})

    def add_channel_attr(self, key: str, value: str) -> None:
        if not key.startswith('Channel-'):
            key = f'Channel-{key}'
        self.mapping.update({key: value})


class E2EApplication(E2EComponent):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.category = 'App'
        self.start_time = ''
        self.stop_time = ''

    def ns3_config(self) -> str:
        self.mapping.update({
            'StartTime': self.start_time,
            'StopTime': self.stop_time,
        })
        return super().ns3_config()


class E2EPacketSinkApplication(E2EApplication):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.type = 'PacketSink'
        self.protocol = 'ns3::TcpSocketFactory'
        self.local_ip = ''

    def ns3_config(self) -> str:
        self.mapping.update({
            'Protocol': self.protocol,
            'Local': self.local_ip,
        })
        return super().ns3_config()


class E2EBulkSendApplication(E2EApplication):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.type = 'BulkSender'
        self.protocol = 'ns3::TcpSocketFactory'
        self.remote_ip = ''

    def ns3_config(self) -> str:
        self.mapping.update({
            'Protocol': self.protocol,
            'Remote': self.remote_ip,
        })
        return super().ns3_config()


class E2ENs3RandomVariable(ABC):

    def __init__(self) -> None:
        self.type_id = ''

    def get_config(self) -> str:
        params = self.get_parameters()
        if params:
            return f'{self.type_id}[{params}]'
        else:
            return self.type_id

    @abstractmethod
    def get_parameters(self) -> str:
        pass


class E2ENs3ConstantRandomVariable(E2ENs3RandomVariable):

    def __init__(self) -> None:
        super().__init__()
        self.type_id = 'ns3::ConstantRandomVariable'
        self.constant: tp.Optional[float] = None

    def get_parameters(self) -> str:
        params = []
        if self.constant:
            params.append(f'Constant={self.constant}')
        return '|'.join(params)


class E2ENs3UniformRandomVariable(E2ENs3RandomVariable):

    def __init__(self) -> None:
        super().__init__()
        self.type_id = 'ns3::UniformRandomVariable'
        self.min: tp.Optional[float] = None
        self.max: tp.Optional[float] = None

    def get_parameters(self) -> str:
        params = []
        if self.min:
            params.append(f'Min={self.min}')
        if self.max:
            params.append(f'Max={self.max}')
        return '|'.join(params)


class E2ENs3ExponentialRandomVariable(E2ENs3RandomVariable):

    def __init__(self) -> None:
        super().__init__()
        self.type_id = 'ns3::ExponentialRandomVariable'
        self.mean: tp.Optional[float] = None
        self.bound: tp.Optional[float] = None

    def get_parameters(self) -> str:
        params = []
        if self.mean:
            params.append(f'Mean={self.mean}')
        if self.bound:
            params.append(f'Bound={self.bound}')
        return '|'.join(params)


class E2ENs3NormalRandomVariable(E2ENs3RandomVariable):

    def __init__(self) -> None:
        super().__init__()
        self.type_id = 'ns3::NormalRandomVariable'
        self.mean: tp.Optional[float] = None
        self.variance: tp.Optional[float] = None
        self.bound: tp.Optional[float] = None

    def get_parameters(self) -> str:
        params = []
        if self.mean:
            params.append(f'Mean={self.mean}')
        if self.variance:
            params.append(f'Variance={self.variance}')
        if self.bound:
            params.append(f'Bound={self.bound}')
        return '|'.join(params)


class E2EOnOffApplication(E2EApplication):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.type = 'OnOff'
        self.protocol = 'ns3::TcpSocketFactory'
        self.remote_ip = ''
        self.data_rate = ''
        self.max_bytes = ''
        self.packet_size = ''
        self.on_time: tp.Optional[E2ENs3RandomVariable] = None
        self.off_time: tp.Optional[E2ENs3RandomVariable] = None

    def ns3_config(self) -> str:
        if self.on_time:
            on = self.on_time.get_config()
        else:
            on = ''
        if self.off_time:
            off = self.off_time.get_config()
        else:
            off = ''
        self.mapping.update({
            'Protocol': self.protocol,
            'Remote': self.remote_ip,
            'DataRate': self.data_rate,
            'MaxBytes': self.max_bytes,
            'PacketSize': self.packet_size,
            'OnTime': on,
            'OffTime': off,
        })
        return super().ns3_config()


class E2EProbe(E2EComponent):

    def __init__(self, idd: str) -> None:
        super().__init__(idd)
        self.category = 'Probe'


class E2EPeriodicSampleProbe(E2EProbe):

    def __init__(self, idd: str, probe_type: str) -> None:
        super().__init__(idd)
        self.type = probe_type
        self.file = ''
        self.header = ''
        self.unit = ''
        self.start = ''
        self.interval = ''

    def ns3_config(self) -> str:
        self.mapping.update({
            'File': self.file,
            'Header': self.header,
            'Unit': self.unit,
            'Start': self.start,
            'Interval': self.interval
        })
        return super().ns3_config()
