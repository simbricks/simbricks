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

from __future__ import annotations

from simbricks.orchestration.system import base
from simbricks.utils import base as utils_base


class EthInterface(base.Interface):
    def __init__(self, c: base.Component) -> None:
        super().__init__(c)

    def connect(self, c: base.Channel) -> None:
        # Note AK: a bit ugly, but I think we can't get around a rt check here
        utils_base.has_expected_type(c, EthChannel)
        super().connect(c)


class EthChannel(base.Channel):
    def __init__(self, a: EthInterface, b: EthInterface) -> None:
        super().__init__(a, b)


class EthSimpleNIC(base.Component):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self._ip: str | None = None
        self._eth_if: EthInterface = EthInterface(self)
        super().add_if(self._eth_if)

    def add_ipv4(self, ip: str) -> None:
        assert self._ip is None
        self._ip = ip

    def add_if(self, interface: EthInterface) -> None:
        utils_base.has_expected_type(interface, EthInterface)
        if hasattr(self, "_eth_if") and self._eth_if:
            raise Exception(
                f"you overwrite EthSimpleNIC._eth_if ({self._eth_if.id()} -> {interface.id()}) "
            )
        self._eth_if = interface
        super().add_if(self._eth_if)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["ip"] = self._ip
        json_obj["eth_if"] = self._eth_if.id()
        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> EthSimpleNIC:
        instance = super().fromJSON(system, json_obj)
        instance._ip = utils_base.get_json_attr_top(json_obj, "ip")
        eth_inf_id = int(utils_base.get_json_attr_top(json_obj, "eth_if"))
        instance._eth_if = system.get_inf(eth_inf_id)
        return instance


class BaseEthNetComponent(base.Component):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)

    def add_if(self, i: EthInterface) -> None:
        utils_base.has_expected_type(i, EthInterface)
        super().add_if(i)

    def toJSON(self) -> dict:
        return super().toJSON()

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> BaseEthNetComponent:
        return super().fromJSON(system, json_obj)


class EthWire(BaseEthNetComponent):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)

    def add_if(self, i: EthInterface) -> None:
        if len(self.ifs) > 2:
            raise Exception("one can only add 2 interfaces to a EthWire")
        super().add_if(i)


class EthSwitch(BaseEthNetComponent):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
