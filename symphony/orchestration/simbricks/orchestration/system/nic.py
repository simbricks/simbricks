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
from simbricks.orchestration.system import pcie
from simbricks.orchestration.system import eth
from simbricks.utils import base as utils_base


class SimplePCIeNIC(base.Component):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self._ip: str | None = None
        self._eth_if: eth.EthInterface = eth.EthInterface(self)
        super().add_if(self._eth_if)
        self._pci_if: pcie.PCIeDeviceInterface = pcie.PCIeDeviceInterface(self)
        super().add_if(self._pci_if)

    def add_if(self, interface: eth.EthInterface | pcie.PCIeDeviceInterface) -> None:
        match interface:
            case eth.EthInterface():
                if hasattr(self, "_eth_if") and self._eth_if:
                    print(interface)
                    print(self._eth_if)
                    raise Exception(
                        f"you overwrite SimplePCIeNIC._eth_if ({self._eth_if.id()} -> {interface.id()}) "
                    )
                self._eth_if = interface
            case pcie.PCIeDeviceInterface():
                if hasattr(self, "_pci_if") and self._pci_if:
                    raise Exception(
                        f"you overwrite SimplePCIeNIC._pci_if. ({self._pci_if.id()} -> {interface.id()})"
                    )
                self._pci_if = interface
            case _:
                raise Exception(
                    f"interface must have type EthInterface or PCIeDeviceInterface but has type {type(interface)}"
                )
        super().add_if(interface)

    def add_ipv4(self, ip: str) -> None:
        assert self._ip is None
        self._ip = ip

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["ip"] = self._ip
        json_obj["eth_if"] = self._eth_if.id()
        json_obj["pci_if"] = self._pci_if.id()
        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> SimplePCIeNIC:
        instance = super().fromJSON(system, json_obj)
        instance._ip = utils_base.get_json_attr_top(json_obj, "ip")
        eth_inf_id = int(utils_base.get_json_attr_top(json_obj, "eth_if"))
        instance._eth_if = system.get_inf(eth_inf_id)
        inf_id = int(utils_base.get_json_attr_top(json_obj, "pci_if"))
        instance._pci_if = system.get_inf(inf_id)
        return instance


class IntelI40eNIC(SimplePCIeNIC):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)


class IntelE1000NIC(SimplePCIeNIC):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)


class CorundumNIC(SimplePCIeNIC):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
