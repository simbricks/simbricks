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


class SimplePCIeNIC(pcie.PCIeSimpleDevice, eth.EthSimpleNIC):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)

    def add_if(self, interface: eth.EthInterface | pcie.PCIeDeviceInterface) -> None:
        match interface:
            case eth.EthInterface():
                eth.EthSimpleNIC.add_if(interface)
            case pcie.PCIeDeviceInterface():
                pcie.PCIeSimpleDevice.add_if(interface)
            case _:
                raise Exception(
                    f"interface must have type EthInterface or PCIeDeviceInterface but has type {type(interface)}"
                )


class IntelI40eNIC(SimplePCIeNIC):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)


class IntelE1000NIC(SimplePCIeNIC):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
