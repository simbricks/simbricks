# Copyright 2022 Max Planck Institute for Software Systems, and
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

"""Additional processes that run inside a single fragment next to its simulators.

A fragment process is anything the fragment executor should spawn alongside the simulators
it runs: a filter that reduces a simulator's debug log to a summary file, a collector that
gathers traces from several simulators, a helper daemon a simulator talks to over a unix
socket. Unlike proxies, processes only depend on components of the same fragment, are not
reported to the backend as components of their own and never take part in cross-fragment
coordination.
"""

from __future__ import annotations

import abc
import enum
import pathlib
import re
import shlex
import typing

import typing_extensions as tpe

from simbricks.orchestration.helpers import exceptions
from simbricks.orchestration.instantiation import proxy as inst_proxy
from simbricks.utils import base as utils_base
from simbricks.utils import file as utils_file

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.instantiation import fragment as inst_fragment
    from simbricks.orchestration.simulation import base as sim_base

FragmentComponent: tpe.TypeAlias = "sim_base.Simulator | inst_proxy.Proxy | FragmentProcess"
"""Anything a process can be ordered against: a simulator, a proxy or another process."""


class StopPolicy(enum.Enum):
    WITH_SIMULATORS = "with_simulators"
    """Stopped together with the simulators when the simulation ends."""
    AFTER_SIMULATORS = "after_simulators"
    """Interrupted only once all simulators and proxies have exited and given `stop_grace_sec`
    to finish on its own, e.g. to flush a summary of a log it follows."""


class FragmentProcess(utils_base.IdObj, utils_base.InputArtifactSource, abc.ABC):
    """A process the fragment executor starts alongside the simulators of a fragment.

    Subclasses implement `run_cmd()`. Start order is expressed with `start_after()` and
    `start_before()`; a process starts once everything it starts after is ready and is ready
    itself once its `ready_files` exist (immediately if there are none).
    """

    def __init__(
        self,
        name: str | None = None,
        stop: StopPolicy = StopPolicy.AFTER_SIMULATORS,
        stop_grace_sec: int = 30,
        wait_terminate: bool = False,
        fail_run_on_error: bool = False,
    ):
        super().__init__()
        self._name: str | None = name
        self.stop: StopPolicy = stop
        self.stop_grace_sec: int = stop_grace_sec
        """Seconds an `AFTER_SIMULATORS` process gets after its interrupt before it is terminated."""
        self.wait_terminate: bool = wait_terminate
        """Like `Simulator.wait_terminate`: the simulation waits for this process to exit."""
        self.fail_run_on_error: bool = fail_run_on_error
        """Fail the simulation when this process exits with a non-zero code before it is stopped."""
        self.ready_files: list[str] = []
        """Files whose existence signals readiness. Path placeholders are resolved."""
        self.output_paths: list[str] = []
        """Files this process produces, relative to the work directory, added to the fragment's
        output artifact."""
        self.input_files: list[str] = []
        """Local files this process needs on the executor, e.g. a script it runs. They are
        shipped in the fragment's input artifact; `input_file_path()` says where they are."""
        self.resreq_cores: int = 0
        self.resreq_mem: int = 0
        self._start_after: set[FragmentComponent] = set()
        self._start_before: set[FragmentComponent] = set()
        # ids kept until the fragment can resolve them, see `resolve_references()`
        self._start_after_ids: list[int] = []
        self._start_before_ids: list[int] = []

    @property
    def name(self) -> str:
        return self._name if self._name is not None else f"process_{self.id()}"

    def start_after(self, *components: FragmentComponent) -> tpe.Self:
        """Start only once all of @components are ready."""
        self._start_after.update(components)
        return self

    def start_before(self, *components: FragmentComponent) -> tpe.Self:
        """Delay the start of @components until this process is ready."""
        self._start_before.update(components)
        return self

    def dependencies(self) -> set[FragmentComponent]:
        return self._start_after

    def dependents(self) -> set[FragmentComponent]:
        return self._start_before

    @abc.abstractmethod
    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        pass

    def input_artifact_files(self) -> list[str]:
        return list(self.input_files)

    def input_file_path(self, inst: inst_base.Instantiation, path: str) -> str:
        """Where the input file @path is on the executor: unpacked from the input artifact when
        one was shipped, otherwise (a local run) where it was picked up."""
        shipped = pathlib.Path(inst.env.input_artifacts_dir(), pathlib.PurePath(path).name)
        if shipped.exists():
            return shipped.as_posix()
        return pathlib.Path(path).resolve().as_posix()

    async def wait_ready(self, inst: inst_base.Instantiation) -> None:
        for path in self.ready_files:
            await utils_file.await_file(inst.resolve_placeholders(path))

    # ------------------
    # (De)serialization -
    # ------------------

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["name"] = self._name
        json_obj["stop"] = self.stop.value
        json_obj["stop_grace_sec"] = self.stop_grace_sec
        json_obj["wait_terminate"] = self.wait_terminate
        json_obj["fail_run_on_error"] = self.fail_run_on_error
        json_obj["ready_files"] = list(self.ready_files)
        json_obj["output_paths"] = list(self.output_paths)
        json_obj["input_files"] = list(self.input_files)
        json_obj["resreq_cores"] = self.resreq_cores
        json_obj["resreq_mem"] = self.resreq_mem
        json_obj["start_after"] = sorted(comp.id() for comp in self._start_after)
        json_obj["start_before"] = sorted(comp.id() for comp in self._start_before)
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance._name = utils_base.get_json_attr_top(json_obj, "name")
        instance.stop = StopPolicy(utils_base.get_json_attr_top(json_obj, "stop"))
        instance.stop_grace_sec = utils_base.get_json_attr_top(json_obj, "stop_grace_sec")
        instance.wait_terminate = utils_base.get_json_attr_top(json_obj, "wait_terminate")
        instance.fail_run_on_error = utils_base.get_json_attr_top(json_obj, "fail_run_on_error")
        instance.ready_files = list(utils_base.get_json_attr_top(json_obj, "ready_files"))
        instance.output_paths = list(utils_base.get_json_attr_top(json_obj, "output_paths"))
        instance.input_files = list(utils_base.get_json_attr_top(json_obj, "input_files"))
        instance.resreq_cores = utils_base.get_json_attr_top(json_obj, "resreq_cores")
        instance.resreq_mem = utils_base.get_json_attr_top(json_obj, "resreq_mem")
        instance._start_after = set()
        instance._start_before = set()
        instance._start_after_ids = list(utils_base.get_json_attr_top(json_obj, "start_after"))
        instance._start_before_ids = list(utils_base.get_json_attr_top(json_obj, "start_before"))
        return instance

    def resolve_references(
        self, simulation: sim_base.Simulation, fragment: inst_fragment.Fragment
    ) -> None:
        """Turn the component ids read by `fromJSON()` back into objects. Called by the fragment
        once all of its components are loaded."""

        def lookup(comp_id: int) -> FragmentComponent:
            for sim in simulation.all_simulators():
                if sim.id() == comp_id:
                    return sim
            for prox in fragment.all_proxies():
                if prox.id() == comp_id:
                    return prox
            for proc in fragment.all_processes():
                if proc.id() == comp_id:
                    return proc
            raise exceptions.InstantiationConfigurationError(
                f"{self.name} references component {comp_id}, which is not part of its fragment"
            )

        self._start_after = {lookup(comp_id) for comp_id in self._start_after_ids}
        self._start_before = {lookup(comp_id) for comp_id in self._start_before_ids}
        self._start_after_ids = []
        self._start_before_ids = []

    def __repr__(self) -> str:
        return self.name


class ShellProcess(FragmentProcess):
    """Runs @cmd through `sh -c`.

    @cmd may use the path placeholders of `InstantiationEnvironment.path_placeholder()`,
    `Instantiation.sim_output_placeholder()` and `ShellProcess.input_file_placeholder()`,
    which are resolved on the executor. @input_files are shipped with the fragment.
    """

    _INPUT_FILE_PLACEHOLDER_RE = re.compile(r"@\{SIMBRICKS_INPUT_FILE:(?P<name>[^}]+)\}@")

    def __init__(self, cmd: str, input_files: list[str] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cmd: str = cmd
        if input_files:
            self.input_files.extend(input_files)

    @staticmethod
    def input_file_placeholder(path: str) -> str:
        """Placeholder for where the input file @path ends up on the executor."""
        return f"@{{SIMBRICKS_INPUT_FILE:{pathlib.PurePath(path).name}}}@"

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        by_name = {pathlib.PurePath(path).name: path for path in self.input_files}

        def resolve_input(match: re.Match[str]) -> str:
            name = match.group("name")
            if name not in by_name:
                raise exceptions.InstantiationConfigurationError(
                    f"{self.name} names input file '{name}', which is not in its input_files"
                )
            return self.input_file_path(inst, by_name[name])

        cmd = self._INPUT_FILE_PLACEHOLDER_RE.sub(resolve_input, self.cmd)
        return shlex.join(["sh", "-c", inst.resolve_placeholders(cmd)])

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["cmd"] = self.cmd
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.cmd = utils_base.get_json_attr_top(json_obj, "cmd")
        return instance
