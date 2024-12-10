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

import json
import time
import pathlib
import typing
from simbricks.runtime import command_executor

if typing.TYPE_CHECKING:
    from simbricks.orchestration.simulation import base as sim_base


class SimulationOutput:
    """Manages an experiment's output."""

    def __init__(self, sim: sim_base.Simulation) -> None:
        self._sim_name: str = sim.name
        self._start_time: float | None = None
        self._end_time: float | None = None
        self._success: bool = True
        self._interrupted: bool = False
        self._metadata = sim.metadata
        self._sims: dict[sim_base.Simulator, command_executor.OutputListener] = {}

    def is_ended(self) -> bool:
        return self._end_time or self._interrupted

    def set_start(self) -> None:
        self._start_time = time.time()

    def set_end(self) -> None:
        self._end_time = time.time()

    def set_failed(self) -> None:
        self._success = False

    def set_interrupted(self) -> None:
        self._success = False
        self._interrupted = True

    def add_mapping(self, sim: sim_base.Simulator, output_handel: command_executor.OutputListener) -> None:
        assert sim not in self._sims
        self._sims[sim] = output_handel

    def get_output_listener(self, sim: sim_base.Simulator) -> command_executor.OutputListener:
        if sim not in self._sims:
            raise Exception("not output handel for simulator found")
        return self._sims[sim]

    def get_all_listeners(self) -> list[command_executor.OutputListener]:
        return list(self._sims.values())

    def toJSON(self) -> dict:
        json_obj = {}
        json_obj["_sim_name"] = self._sim_name
        json_obj["_start_time"] = self._start_time
        json_obj["_end_time"] = self._end_time
        json_obj["_success"] = self._success
        json_obj["_interrupted"] = self._interrupted
        json_obj["_metadata"] = self._metadata
        for sim, out in self._sims.items():
            json_obj[sim.full_name()] = out.toJSON()
            json_obj["class"] = sim.__class__.__name__
        return json_obj

    def dump(self, outpath: str) -> None:
        json_obj = self.toJSON()
        pathlib.Path(outpath).parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w", encoding="utf-8") as file:
            json.dump(json_obj, file, indent=4)

    # def load(self, file: str) -> None:
    #     with open(file, "r", encoding="utf-8") as fp:
    #         for k, v in json.load(fp).items():
    #             self.__dict__[k] = v
