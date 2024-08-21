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
import simbricks.orchestration.system.pcie as pcie
import simbricks.orchestration.system.eth as eth


class SimplePCIeNIC(pcie.PCIeSimpleDevice, eth.EthSimpleNIC):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)

    def interfaces(self) -> tp.List[base.Interface]:
        return [self.pci_if, self.eth_if]


class IntelI40eNIC(SimplePCIeNIC):
    pass


class IntelE1000NIC(SimplePCIeNIC):
    pass


class CorundumNIC(SimplePCIeNIC):
    pass