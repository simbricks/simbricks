# Copyright 2024 Max Planck Institute for Software Systems, and
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

from simbricks.orchestration.system.base import (
    Channel,
    Component,
    DummyComponent,
    DummyInterface,
    Interface,
    System,
)

__all__ = [
    "System",
    "Component",
    "DummyComponent",
    "Interface",
    "DummyInterface",
    "Channel",
]

from simbricks.orchestration.system.pcie import (
    NVMeSSD,
    PCIeChannel,
    PCIeDeviceInterface,
    PCIeHostInterface,
    PCIeSimpleDevice,
)

__all__ += [
    "PCIeHostInterface",
    "PCIeDeviceInterface",
    "PCIeChannel",
    "PCIeSimpleDevice",
    "NVMeSSD",
]

from simbricks.orchestration.system.eth import (
    BaseEthNetComponent,
    EthChannel,
    EthInterface,
    EthSimpleNIC,
    EthSwitch,
    EthWire,
)

__all__ += [
    "EthInterface",
    "EthChannel",
    "EthSimpleNIC",
    "BaseEthNetComponent",
    "EthWire",
    "EthSwitch",
]

from simbricks.orchestration.system.mem import (
    MemChannel,
    MemDeviceInterface,
    MemHostInterface,
    MemInterconnect,
    MemSimpleDevice,
    MemTerminal,
)

__all__ += [
    "MemHostInterface",
    "MemDeviceInterface",
    "MemChannel",
    "MemSimpleDevice",
    "MemInterconnect",
    "MemTerminal",
]

from simbricks.orchestration.system.nic import (
    SimplePCIeNIC,
)

__all__ += [
    "SimplePCIeNIC",
]

from simbricks.orchestration.system.disk_images import (
    ConfigFile,
    ConfigFileLocal,
    ConfigFileStr,
    DiskImage,
    DistroDiskImage,
    DummyDiskImage,
    DynamicDiskImage,
    ExternalDiskImage,
    LinuxConfigDiskImage,
    PackerDiskImage,
)

__all__ += [
    "DiskImage",
    "DummyDiskImage",
    "ExternalDiskImage",
    "DistroDiskImage",
    "DynamicDiskImage",
    "LinuxConfigDiskImage",
    "PackerDiskImage",
    "ConfigFile",
    "ConfigFileLocal",
    "ConfigFileStr",
]

from simbricks.orchestration.system.host import (
    # app.py
    Application,
    BaseLinuxApplication,
    BaseLinuxHost,
    FullSystemHost,
    GenericRawCommandApplication,
    # base.py
    Host,
    IperfTCPClient,
    IperfTCPServer,
    IperfUDPClient,
    IperfUDPServer,
    LinuxHost,
    NetperfClient,
    NetperfServer,
    NVMEFsTest,
    NVMeLinuxHost,
    PingClient,
    Sleep,
)

__all__ += [
    # base.py
    "Host",
    "FullSystemHost",
    "BaseLinuxHost",
    "LinuxHost",
    "NVMeLinuxHost",
    # app.py
    "Application",
    "BaseLinuxApplication",
    "GenericRawCommandApplication",
    "NVMEFsTest",
    "PingClient",
    "Sleep",
    "NetperfServer",
    "NetperfClient",
    "IperfTCPServer",
    "IperfUDPServer",
    "IperfTCPClient",
    "IperfUDPClient",
]
