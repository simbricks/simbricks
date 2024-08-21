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

import typing as tp

import simbricks.orchestration.system.base as base


class MemHostInterface(base.Interface):
    # Note AK: Component here is on purpose. Other simulators than host
    # simulators can also have MemHost interfaces (e.g. a Mem switch)
    def __init__(self, c: base.Component) -> None:
        super().__init__(c)


class MemDeviceInterface(base.Interface):
    def __init__(self, c: base.Component) -> None:
        super().__init__(c)

    def connect(self, c: base.Channel) -> None:
        # Note AK: a bit ugly, but I think we can't get around a rt check here
        if not c is isinstance(c, MemChannel):
            raise TypeError('MemDeviceInterface only connects to MemChannel')
        super().connect(c)


class MemChannel(base.Channel):
    def __init__(self, host: MemHostInterface, dev: MemDeviceInterface) -> None:
        super().__init__(host, dev)

    def host_if(self) -> MemHostInterface:
        return self.a
    
    def dev_if(self) -> MemDeviceInterface:
        return self.b


class MemSimpleDevice(base.Component):
    def __init__(self, s: base.System):
        super().__init__(s)
        self.mem_if = MemDeviceInterface()

    def interfaces(self) -> tp.List[base.Interface]:
        return [self.mem_if]