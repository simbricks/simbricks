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

import asyncio
import pathlib

from simbricks.runtime.common import *
import simbricks.experiments as exp
import simbricks.exectools as exectools

class DistributedSimpleRuntime(Runtime):
    def __init__(self, execs, verbose=False):
        self.runnable = []
        self.complete = []
        self.verbose = verbose
        self.execs = execs

    def add_run(self, run):
        self.runnable.append(run)

    async def do_run(self, run):
        runner = exp.ExperimentDistributedRunner(self.execs, run.experiment,
            run.env, self.verbose)
        for exec in self.execs:
            await run.prep_dirs(exec)
        await runner.prepare()
        run.output = await runner.run()
        self.complete.append(run)

        pathlib.Path(run.outpath).parent.mkdir(parents=True, exist_ok=True)
        with open(run.outpath, 'w') as f:
            f.write(run.output.dumps())

    def start(self):
        for run in self.runnable:
            asyncio.run(self.do_run(run))