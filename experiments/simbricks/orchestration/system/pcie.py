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

from simbricks.orchestration.system import base


class PCIeHostInterface(base.Interface):
    # Note AK: Component here is on purpose. Other simulators than host
    # simulators can also have PCIeHost interfaces (e.g. a PCIe switch)
    def __init__(self, c: base.Component) -> None:
        super().__init__(c)


class PCIeDeviceInterface(base.Interface):
    def __init__(self, c: base.Component) -> None:
        super().__init__(c)

    def connect(self, c: base.Channel) -> None:
        # Note AK: a bit ugly, but I think we can't get around a rt check here
        if not c is isinstance(c, PCIeChannel):
            raise TypeError('PCIeDeviceInterface only connects to PCIeChannel')
        super().connect(c)


class PCIeChannel(base.Channel):
    def __init__(self, host: PCIeHostInterface, dev: PCIeDeviceInterface) -> None:
        super().__init__(host, dev)

    def host_if(self) -> PCIeHostInterface:
        return self.a
    
    def dev_if(self) -> PCIeDeviceInterface:
        return self.b


# Note AK: Can we make this abstract?
class PCIeSimpleDevice(base.Component):
    def __init__(self, s: base.System):
        super().__init__(s)
        self.pci_if = PCIeDeviceInterface(self)

    def interfaces(self) -> list[base.Interface]:
        return [self.pci_if]