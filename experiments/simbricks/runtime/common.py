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

# Allow type annotation of class to be used in its own constructor
from __future__ import annotations

from abc import abstractmethod
import shutil
import pathlib
import typing as tp

from simbricks.experiment.experiment_environment import ExpEnv
from simbricks.experiment.experiment_output import ExpOutput
from simbricks.experiments import Experiment
import simbricks.exectools as exectools


class Run(object):
    """Defines a single execution run for an experiment."""

    def __init__(
        self,
        experiment: Experiment,
        index: int,
        env: ExpEnv,
        outpath: str,
        prereq: tp.Optional[Run] = None
    ):
        self.experiment = experiment
        self.index = index
        self.env = env
        self.outpath = outpath
        self.output: tp.Optional[ExpOutput] = None
        self.prereq = prereq

    def name(self):
        return self.experiment.name + '.' + str(self.index)

    async def prep_dirs(self, exec=exectools.LocalExecutor()):
        shutil.rmtree(self.env.workdir, ignore_errors=True)
        await exec.rmtree(self.env.workdir)
        shutil.rmtree(self.env.shm_base, ignore_errors=True)
        await exec.rmtree(self.env.shm_base)

        if self.env.create_cp:
            shutil.rmtree(self.env.cpdir, ignore_errors=True)
            await exec.rmtree(self.env.cpdir)

        pathlib.Path(self.env.workdir).mkdir(parents=True, exist_ok=True)
        await exec.mkdir(self.env.workdir)
        pathlib.Path(self.env.cpdir).mkdir(parents=True, exist_ok=True)
        await exec.mkdir(self.env.cpdir)
        pathlib.Path(self.env.shm_base).mkdir(parents=True, exist_ok=True)
        await exec.mkdir(self.env.shm_base)


class Runtime(object):
    """Base class for managing the execution of multiple runs."""

    @abstractmethod
    def add_run(self, run: Run):
        pass

    @abstractmethod
    def start(self):
        pass