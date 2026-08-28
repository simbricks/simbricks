# Copyright 2021 Max Planck Institute for Software Systems, and
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

# Allow own class to be used as type for a method's argument
from __future__ import annotations

import abc
import itertools
import pathlib

from simbricks.orchestration.instantiation import base as inst_base
from simbricks.runtime import output
from simbricks.utils import artifatcs as utils_art
from simbricks.utils import file as utils_file


class Run:
    """Defines a single execution run for an experiment."""

    __run_nr = itertools.count()

    def __init__(
        self,
        instantiation: inst_base.Instantiation,
        prereq: Run | None = None,
        simulation_output: output.SimulationOutput | None = None,
        job_id: int | None = None,
        cp: bool = False,
    ):
        self.instantiation: inst_base.Instantiation = instantiation
        self._run_nr = next(self.__run_nr)
        self._output: output.SimulationOutput | None = simulation_output
        self._prereq: Run | None = prereq
        self.checkpoint: bool = cp

    def name(self) -> str:
        return self.instantiation.simulation.name + "." + str(self._run_nr)


class Runtime(metaclass=abc.ABCMeta):
    """Base class for managing the execution of multiple runs."""

    def __init__(self) -> None:
        self._interrupted = False
        """Indicates whether interrupt has been signaled."""
        self._profile_int: int | None = None

    @abc.abstractmethod
    def add_run(self, run: Run) -> None:
        pass

    @abc.abstractmethod
    async def start(self) -> None:
        pass

    @abc.abstractmethod
    def interrupt_handler(self) -> None:
        """
        Interrupts signal handler.

        All currently running simulators should be stopped cleanly and their
        output collected.
        """
        pass

    def interrupt(self) -> None:
        """Signals interrupt to runtime."""

        # don't invoke interrupt handler multiple times as this would trigger
        # repeated CancelledError
        if not self._interrupted:
            self._interrupted = True
            self.interrupt_handler()

    def enable_profiler(self, profile_int: int) -> None:
        self._profile_int = profile_int

    async def _store_output_artifact(self, run: Run) -> None:
        """Pack the run's output artifact into its output directory."""
        fragment = run.instantiation.assigned_fragment
        if not fragment.output_artifact_paths:
            return

        work_dir = pathlib.Path(run.instantiation.env.work_dir())
        output_base = pathlib.Path(run.instantiation.env.output_base())

        sink = utils_art.LocalFsArtifactSink(output_base)
        await sink.produce(
            utils_art.ArtifactInfo(
                kind=utils_art.ArtifactKind.OUTPUT,
                name=fragment.output_artifact_name,
                run_id=str(run.instantiation.id()),
                # No backend here to hand out ids, so the fragment identifies itself.
                run_fragment_id=str(fragment.id()),
            ),
            paths_to_include=fragment.output_artifact_paths,
            base_path=work_dir,
            staging_dir=work_dir.parent,
        )
