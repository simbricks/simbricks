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
import simbricks.orchestration.system.base as system_base
import simbricks.orchestration.simulation.base as sim_base


class Channel(sim_base.Simulator):

    def __init__(self, e: sim_base.Simulation, chan: system_base.Channel):
        super().__init__(e)
        self._synchronized: bool = True
        self.sync_period: int = 500  # nano second
        self.sys_channel: system_base.Channel = chan

    def full_name(self) -> str:
        return "channel." + self.name

    # def add(self, ch: system_base.Channel):
    #     self.sys_channel = ch
    #     self.name = f"{ch.id}"
    #     self.experiment.sys_sim_map[ch] = self
