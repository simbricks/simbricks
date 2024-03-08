# Copyright 2023 Max Planck Institute for Software Systems, and
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

import asyncio
import typing as tp

from simbricks.orchestration.runners import ExperimentDryRunner
from simbricks.orchestration.runtime.common import Run, Runtime


class DryRuntime(Runtime):
    """Execute dry runs."""

    def __init__(
        self,
        verbose=False,
    ):
        super().__init__()
        self.runnable: tp.List[Run] = []
        self.verbose = verbose
        self._running: tp.Optional[asyncio.Task] = None

    def add_run(self, run: Run) -> None:
        self.runnable.append(run)

    async def do_run(self, run: Run) -> None:
        """Actually executes `run`."""
        runner = ExperimentDryRunner(run.experiment, run.env, self.verbose)
        await runner.run()  # handles CancelledError

    async def start(self) -> None:
        """Execute the runs defined in `self.runnable`."""
        for run in self.runnable:
            if self._interrupted:
                return

            self._running = asyncio.create_task(self.do_run(run))
            await self._running

    def interrupt_handler(self) -> None:
        if self._running:
            self._running.cancel()
