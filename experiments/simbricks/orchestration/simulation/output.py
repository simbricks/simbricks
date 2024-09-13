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

from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.runtime_new import command_executor

class SimulationOutput:
    """Manages an experiment's output."""

    def __init__(self, sim: sim_base.Simulation) -> None:
        self._sim_name: str = sim.name
        self._start_time: float = None
        self._end_time: float = None
        self._success: bool = True
        self._interrupted: bool = False
        self._metadata = sim.metadata
        self._sims: dict[str, dict[str, str | list[str]]] = {}

    def set_start(self) -> None:
        self._start_time = time.time()

    def set_end(self) -> None:
        self._end_time = time.time()

    def set_failed(self) -> None:
        self._success = False

    def set_interrupted(self) -> None:
        self._success = False
        self._interrupted = True

    def add_sim(self, sim: sim_base.Simulator, comp: command_executor.Component) -> None:
        obj = {
            "class": sim.__class__.__name__,
            "cmd": comp.cmd_parts,
            "stdout": comp.stdout,
            "stderr": comp.stderr,
        }
        self._sims[sim.full_name()] = obj

    def dump(self, outpath: str) -> None:
        pathlib.Path(outpath).parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w", encoding="utf-8") as file:
            json.dump(self.__dict__, file, indent=4)

    def load(self, file: str) -> None:
        with open(file, "r", encoding="utf-8") as fp:
            for k, v in json.load(fp).items():
                self.__dict__[k] = v

