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

import collections
import enum
import json
import pathlib
import time
import typing

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import proxy as inst_proxy
    from simbricks.orchestration.simulation import base as sim_base


class SimulationExitState(enum.Enum):
    SUCCESS = 0
    FAILED = 1
    INTERRUPTED = 2


class ProcessOutput:

    def __init__(self, cmd: str):
        self.cmd = cmd
        self.stdout: list[str] = []
        self.stderr: list[str] = []
        self.merged: list[str] = []

    def append_stdout(self, lines: list[str]) -> None:
        self.stdout.extend(lines)
        self.merged.extend(lines)

    def append_stderr(self, lines: list[str]) -> None:
        self.stderr.extend(lines)
        self.merged.extend(lines)

    def toJSON(self) -> dict:
        return {
            "cmd": self.cmd,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "merged_output": self.merged,
        }


class SimulationOutput:
    """Manages an experiment's output."""

    def __init__(self, sim: sim_base.Simulation) -> None:
        self._simulation_name: str = sim.name
        self._start_time: float | None = None
        self._end_time: float | None = None
        self._success: bool = True
        self._interrupted: bool = False
        self._metadata = sim.metadata
        self._generic_prepare_output: dict[str, ProcessOutput] = {}
        self._simulator_output: collections.defaultdict[sim_base.Simulator, list[ProcessOutput]] = (
            collections.defaultdict(list)
        )
        self._proxy_output: collections.defaultdict[inst_proxy.Proxy, list[ProcessOutput]] = {}

    def is_ended(self) -> bool:
        return self._end_time or self._interrupted

    def set_start(self) -> None:
        self._start_time = time.time()

    def set_end(self, exit_state: SimulationExitState) -> None:
        self._end_time = time.time()
        match exit_state:
            case SimulationExitState.SUCCESS:
                self._success = True
            case SimulationExitState.FAILED:
                self._success = False
            case SimulationExitState.INTERRUPTED:
                self._success = False
                self._interrupted = True
            case _:
                raise RuntimeError("Unknown simulation exit state")

    def failed(self) -> bool:
        return not self._success

    # generic prepare command execution
    def add_generic_prepare_cmd(self, cmd: str) -> None:
        self._generic_prepare_output[cmd] = ProcessOutput(cmd)

    def generic_prepare_cmd_stdout(self, cmd: str, lines: list[str]) -> None:
        assert cmd in self._generic_prepare_output
        self._generic_prepare_output[cmd].append_stdout(lines)

    def generic_prepare_cmd_stderr(self, cmd: str, lines: list[str]) -> None:
        assert cmd in self._generic_prepare_output
        self._generic_prepare_output[cmd].append_stderr(lines)

    # simulator execution
    def set_simulator_cmd(self, sim: sim_base.Simulator, cmd: str) -> None:
        self._simulator_output[sim].append(ProcessOutput(cmd))

    def append_simulator_stdout(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        assert sim in self._simulator_output
        assert self._simulator_output[sim]
        self._simulator_output[sim][-1].append_stdout(lines)

    def append_simulator_stderr(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        assert sim in self._simulator_output
        assert self._simulator_output[sim]
        self._simulator_output[sim][-1].append_stderr(lines)

    def set_proxy_cmd(self, proxy: inst_proxy.Proxy, cmd: str) -> None:
        self._proxy_output[proxy].append(ProcessOutput(cmd))

    def append_proxy_stdout(self, proxy: inst_proxy.Proxy, lines: list[str]) -> None:
        assert proxy in self._proxy_output
        self._proxy_output[proxy][-1].append_stdout(lines)

    def append_proxy_stderr(self, proxy: inst_proxy.Proxy, lines: list[str]) -> None:
        assert proxy in self._proxy_output
        self._proxy_output[proxy][-1].append_stderr(lines)

    def toJSON(self) -> dict:
        json_obj = {}
        json_obj["_sim_name"] = self._simulation_name
        json_obj["_start_time"] = self._start_time
        json_obj["_end_time"] = self._end_time
        json_obj["_success"] = self._success
        json_obj["_interrupted"] = self._interrupted
        json_obj["_metadata"] = self._metadata
        # TODO (Jonas) Change backend to reflect multiple commands executed
        json_obj_out_list = []
        for _, proc_out in self._generic_prepare_output.items():
            json_obj_out_list.append(proc_out.toJSON())
        json_obj["generic_prepare"] = json_obj_out_list
        for sim, proc_list in self._simulator_output.items():
            json_obj_out_list = []
            for proc_out in proc_list:
                json_obj_out_list.append(proc_out.toJSON())
            json_obj[sim.full_name()] = {
                "class": sim.__class__.__name__,
                "output": json_obj_out_list,
            }
        for proxy, proc_list in self._proxy_output.items():
            json_obj_out_list = []
            for proc_out in proc_list:
                json_obj_out_list.append(proc_out.toJSON())
            json_obj[proxy.name] = {"class": proxy.__class__.__name__, "output": json_obj_out_list}

        return json_obj

    def dump(self, outpath: str) -> None:
        json_obj = self.toJSON()
        pathlib.Path(outpath).parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w", encoding="utf-8") as file:
            json.dump(json_obj, file, indent=2)
