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

import pickle
import os
import pathlib
import re

from simbricks.runtime.common import *

class SlurmRuntime(Runtime):
    def __init__(self, slurmdir, args, verbose=False, cleanup=True):
        self.runnable = []
        self.slurmdir = slurmdir
        self.args = args
        self.verbose = verbose
        self.cleanup = cleanup

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
        with open(exp_path, 'wb') as f:
            run.prereq = None # we don't want to pull in the prereq too
            pickle.dump(run, f)

        # create slurm batch script
        with open(exp_script, 'w') as f:
            f.write('#!/bin/sh\n')
            f.write('#SBATCH -o %s -e %s\n' % (exp_log, exp_log))
            #f.write('#SBATCH -c %d\n' % (exp.resreq_cores(),))
            f.write('#SBATCH --mem=%dM\n' % (exp.resreq_mem(),))
            f.write('#SBATCH --job-name="%s"\n' % (run.name(),))
            f.write('#SBATCH --exclude=spyder[01-05],spyder16\n')
            f.write('#SBATCH -c 32\n')
            f.write('#SBATCH --nodes=1\n')
            if exp.timeout is not None:
                h = int(exp.timeout / 3600)
                m = int((exp.timeout % 3600) / 60)
                s = int(exp.timeout % 60)
                f.write('#SBATCH --time=%02d:%02d:%02d\n' % (h, m, s))

            extra = ''
            if self.verbose:
                extra = '--verbose'

            f.write('python3 run.py %s --pickled %s\n' % (extra, exp_path))
            f.write('status=$?\n')
            if self.cleanup:
                f.write('rm -rf %s\n' % (run.env.workdir))
            f.write('exit $status\n')

        return exp_script

    def start(self):
        pathlib.Path(self.slurmdir).mkdir(parents=True, exist_ok=True)

        jid_re = re.compile(r'Submitted batch job ([0-9]+)')

        for run in self.runnable:
            if run.prereq is None:
                dep_cmd = ''
            else:
                dep_cmd = '--dependency=afterok:' + str(run.prereq.job_id)

            script = self.prep_run(run)

            stream = os.popen('sbatch %s %s' % (dep_cmd, script))
            output = stream.read()
            result = stream.close()

            if result is not None:
                raise Exception('running sbatch failed')

            m = jid_re.search(output)
            run.job_id = int(m.group(1))
