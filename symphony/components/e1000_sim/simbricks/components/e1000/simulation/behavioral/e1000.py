# Copyright 2026 Max Planck Institute for Software Systems,
# National University of Singapore, and SimBricks UG (haftungsbeschränkt)
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

import typing_extensions as tpe

from simbricks.components.e1000 import system as e1000_sys
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.simulation import pcidev
from simbricks.utils import base as utils_base


class E1000NIC(pcidev.NICSim):

    def __init__(self, simulation: sim_base.Simulation):
        super().__init__(
            simulation=simulation,
            executable="sims/nic/e1000_gem5/e1000_gem5",
        )
        self.name = f"NICSim-{self._id}"
        self.debug: bool = False

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["debug"] = self.debug
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(simulation, json_obj)
        instance.debug = utils_base.get_json_attr_top(json_obj, "debug")
        return instance

    def add(self, nic: e1000_sys.IntelE1000NIC):
        utils_base.has_expected_type(nic, e1000_sys.IntelE1000NIC)
        super().add(nic)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst)
        if self.mac:
            cmd += " " + ("".join(reversed(self.mac.split(":"))))
            if self.log_file:
                cmd += f" {self.log_file}"

        if self.debug:
            cmd = f"env E1000_DEBUG=1 {cmd}"

        return cmd
