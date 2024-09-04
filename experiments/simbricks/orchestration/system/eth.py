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


class EthInterface(base.Interface):
    def __init__(self, c: base.Component) -> None:
        super().__init__(c)

    def connect(self, c: base.Channel) -> None:
        # Note AK: a bit ugly, but I think we can't get around a rt check here
        if not c is isinstance(c, EthChannel):
            raise TypeError("EthInterface only connects to EthChannel")
        super().connect(c)


class EthChannel(base.Channel):
    def __init__(self, a: EthInterface, b: EthInterface) -> None:
        super().__init__(a, b)


class EthSimpleNIC(base.Component):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.eth_if = EthInterface(self)


class BaseEthNetComponent(base.Component):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.eth_ifs: EthInterface = []

    def if_add(self, i: EthInterface) -> None:
        self.eth_ifs.append(i)

    def interfaces(self) -> list[EthInterface]:
        return self.eth_ifs


class EthWire(BaseEthNetComponent):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)

    def if_add(self, i: EthInterface) -> None:
        if len(self.eth_ifs) > 2:
            raise Exception("one can only add 2 interfaces to a EthWire")
        self.eth_ifs.append(i)


class EthSwitch(BaseEthNetComponent):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
