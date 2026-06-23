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
    System,
    Component,
    DummyComponent,
    Interface,
    DummyInterface,
    Channel,
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
    PCIeHostInterface,
    PCIeDeviceInterface,
    PCIeChannel,
    PCIeSimpleDevice,
    NVMeSSD,
)

__all__ += [
    "PCIeHostInterface",
    "PCIeDeviceInterface",
    "PCIeChannel",
    "PCIeSimpleDevice",
    "NVMeSSD",
]

from simbricks.orchestration.system.eth import (
    EthInterface,
    EthChannel,
    EthSimpleNIC,
    BaseEthNetComponent,
    EthWire,
    EthSwitch,
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
    MemHostInterface,
    MemDeviceInterface,
    MemChannel,
    MemSimpleDevice,
    MemInterconnect,
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
    IntelE1000NIC,
)

__all__ += [
    "SimplePCIeNIC",
    "IntelE1000NIC",
]

from simbricks.orchestration.system.disk_images import (
    DiskImage,
    DummyDiskImage,
    ExternalDiskImage,
    DistroDiskImage,
    DynamicDiskImage,
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
]

from simbricks.orchestration.system.host import (
    # base.py
    Host,
    FullSystemHost,
    BaseLinuxHost,
    LinuxHost,
    E1000LinuxHost,
    NVMeLinuxHost,
    # app.py
    Application,
    BaseLinuxApplication,
    GenericRawCommandApplication,
    NVMEFsTest,
    PingClient,
    Sleep,
    NetperfServer,
    NetperfClient,
    IperfTCPServer,
    IperfUDPServer,
    IperfTCPClient,
    IperfUDPClient,
)

__all__ += [
    # base.py
    "Host",
    "FullSystemHost",
    "BaseLinuxHost",
    "LinuxHost",
    "E1000LinuxHost",
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
