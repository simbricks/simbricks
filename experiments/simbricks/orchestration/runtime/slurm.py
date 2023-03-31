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
import os
import pathlib
import pickle
import re
import typing as tp

from simbricks.orchestration.runtime.common import Run, Runtime


class SlurmRuntime(Runtime):

    def __init__(self, slurmdir, args, verbose=False, cleanup=True):
        super().__init__()
        self.runnable: tp.List[Run] = []
        self.slurmdir = slurmdir
        self.args = args
        self.verbose = verbose
        self.cleanup = cleanup

        self._start_task: asyncio.Task

    def add_run(self, run: Run):
        self.runnable.append(run)

    def prep_run(self, run: Run):
        exp = run.experiment
        e_idx = exp.name + f'-{run.index}' + '.exp'
        exp_path = os.path.join(self.slurmdir, e_idx)

        log_idx = exp.name + f'-{run.index}' + '.log'
        exp_log = os.path.join(self.slurmdir, log_idx)

        sc_idx = exp.name + f'-{run.index}' + '.sh'
        exp_script = os.path.join(self.slurmdir, sc_idx)
        print(exp_path)
        print(exp_log)
        print(exp_script)

        # write out pickled run
        with open(exp_path, 'wb', encoding='utf-8') as f:
            run.prereq = None  # we don't want to pull in the prereq too
            pickle.dump(run, f)

        # create slurm batch script
        with open(exp_script, 'w', encoding='utf-8') as f:
            f.write('#!/bin/sh\n')
            f.write(f'#SBATCH -o {exp_log} -e {exp_log}\n')
            #f.write('#SBATCH -c %d\n' % (exp.resreq_cores(),))
            f.write(f'#SBATCH --mem={exp.resreq_mem()}M\n')
            f.write(f'#SBATCH --job-name="{run.name()}"\n')
            f.write('#SBATCH --exclude=spyder[01-05],spyder16\n')
            f.write('#SBATCH -c 32\n')
            f.write('#SBATCH --nodes=1\n')
            if exp.timeout is not None:
                h = int(exp.timeout / 3600)
                m = int((exp.timeout % 3600) / 60)
                s = int(exp.timeout % 60)
                f.write(f'#SBATCH --time={h:02d}:{m:02d}:{s:02d}\n')

            extra = ''
            if self.verbose:
                extra = '--verbose'

            f.write(f'python3 run.py {extra} --pickled {exp_path}\n')
            f.write('status=$?\n')
            if self.cleanup:
                f.write(f'rm -rf {run.env.workdir}\n')
            f.write('exit $status\n')

        return exp_script

    async def _do_start(self):
        pathlib.Path(self.slurmdir).mkdir(parents=True, exist_ok=True)

        jid_re = re.compile(r'Submitted batch job ([0-9]+)')

        for run in self.runnable:
            if run.prereq is None:
                dep_cmd = ''
            else:
                dep_cmd = '--dependency=afterok:' + str(run.prereq.job_id)

            script = self.prep_run(run)

            stream = os.popen(f'sbatch {dep_cmd} {script}')
            output = stream.read()
            result = stream.close()

            if result is not None:
                raise RuntimeError('running sbatch failed')

            m = jid_re.search(output)
            if m is None:
                raise RuntimeError('cannot retrieve id of submitted job')
            run.job_id = int(m.group(1))

    async def start(self):
        self._start_task = asyncio.create_task(self._do_start())
        try:
            await self._start_task
        except asyncio.CancelledError:
            # stop all runs that have already been scheduled
            # (existing slurm job id)
            job_ids = []
            for run in self.runnable:
                if run.job_id:
                    job_ids.append(str(run.job_id))

            scancel_process = await asyncio.create_subprocess_shell(
                f"scancel {' '.join(job_ids)}"
            )
            await scancel_process.wait()

    def interrupt(self):
        super().interrupt()
        self._start_task.cancel()
