import asyncio
import pickle
import os
import pathlib

import modes.experiments as exp

class Run(object):
    def __init__(self, experiment, index, env, outpath):
        self.experiment = experiment
        self.index = index
        self.env = env
        self.outpath = outpath
        self.output = None

    def name(self):
        return self.experiment.name + '.' + str(self.index)

class Runtime(object):
    def add_run(self, run):
        pass

    def start(self):
        pass


class LocalSimpleRuntime(Runtime):
    def __init__(self, verbose=False):
        self.runnable = []
        self.complete = []
        self.verbose = verbose

    def add_run(self, run):
        self.runnable.append(run)

    def start(self):
        for run in self.runnable:
            run.output = exp.run_exp_local(run.experiment, run.env,
                    verbose=self.verbose)
            self.complete.append(run)

            with open(run.outpath, 'w') as f:
                f.write(run.output.dumps())


class LocalParallelRuntime(Runtime):
    def __init__(self, cores, mem=None, verbose=False):
        self.runnable = []
        self.complete = []
        self.cores = cores
        self.mem = mem
        self.verbose = verbose

    def add_run(self, run):
        if run.experiment.resreq_cores() > self.cores:
            raise Exception('Not enough cores available for run')

        if self.mem is not None and run.experiment.resreq_mem() > self.mem:
            raise Exception('Not enough memory available for run')

        self.runnable.append(run)

    async def do_run(self, run):
        ''' actually starts a run '''
        await run.experiment.prepare(run.env, verbose=self.verbose)
        print('starting run ', run.name())
        run.output = await run.experiment.run(run.env, verbose=self.verbose)
        with open(run.outpath, 'w') as f:
            f.write(run.output.dumps())
        print('finished run ', run.name())
        return run

    async def wait_completion(self):
        ''' wait for any run to terminate and return '''
        assert self.pending_jobs

        done, self.pending_jobs = await asyncio.wait(self.pending_jobs,
                return_when=asyncio.FIRST_COMPLETED)

        for run in done:
            run = await run
            self.complete.append(run)
            self.cores_used -= run.experiment.resreq_cores()
            self.mem_used -= run.experiment.resreq_mem()

    def enough_resources(self, run):
        ''' check if enough cores and mem are available for the run '''
        exp = run.experiment

        if self.cores is not None:
            enough_cores = (self.cores - self.cores_used) >= exp.resreq_cores()
        else:
            enough_cores = True

        if self.mem is not None:
            enough_mem = (self.mem - self.mem_used) >= exp.resreq_mem()
        else:
            enough_mem = True

        return enough_cores and enough_mem

    async def do_start(self):
        #self.completions = asyncio.Queue()
        self.cores_used = 0
        self.mem_used = 0
        self.pending_jobs = set()

        for run in self.runnable:
            # check if we first have to wait for memory or cores
            while not self.enough_resources(run):
                print('waiting for resources')
                await self.wait_completion()

            self.cores_used += run.experiment.resreq_cores()
            self.mem_used += run.experiment.resreq_mem()

            job = self.do_run(run)
            self.pending_jobs.add(job)

        # wait for all runs to finish
        while self.pending_jobs:
            await self.wait_completion()

    def start(self):
        asyncio.run(self.do_start())

class SlurmRuntime(Runtime):
    def __init__(self, slurmdir, args, verbose=False, cleanup=True):
        self.runnable = []
        self.slurmdir = slurmdir
        self.args = args
        self.verbose = verbose
        self.cleanup = cleanup

    def add_run(self, run):
        self.runnable.append(run)

    def prep_run(self, run):
        exp = run.experiment
        exp_path = '%s/%s-%d.exp' % (self.slurmdir, exp.name, run.index)
        exp_log = '%s/%s-%d.log' % (self.slurmdir, exp.name, run.index)
        exp_script = '%s/%s-%d.sh' % (self.slurmdir, exp.name, run.index)

        # write out pickled experiment
        with open(exp_path, 'wb') as f:
            pickle.dump(exp, f)

        # create slurm batch script
        with open(exp_script, 'w') as f:
            f.write('#!/bin/sh\n')
            f.write('#SBATCH -o %s -e %s\n' % (exp_log, exp_log))
            f.write('#SBATCH -c %d\n' % (exp.resreq_cores(),))
            f.write('#SBATCH --mem=%dM\n' % (exp.resreq_mem(),))
            f.write('#SBATCH --job-name="%s"\n' % (run.name(),))
            if exp.timeout is not None:
                h = int(exp.timeout / 3600)
                m = int((exp.timeout % 3600) / 60)
                s = int(exp.timeout % 60)
                f.write('#SBATCH --time=%02d:%02d:%02d\n' % (h, m, s))

            f.write('mkdir -p %s\n' % (self.args.workdir))
            f.write(('python3 run.py --repo=%s --workdir=%s --outdir=%s '
                '--firstrun=%d --runs=1 %s\n') % (self.args.repo,
                    self.args.workdir, self.args.outdir, run.index,
                    exp_path))
            f.write('status=$?\n')
            if self.cleanup:
                f.write('rm -rf %s\n' % (run.env.workdir))
            f.write('exit $status\n')

        return exp_script

    def start(self):
        pathlib.Path(self.slurmdir).mkdir(parents=True, exist_ok=True)

        for run in self.runnable:
            script = self.prep_run(run)
            os.system('sbatch ' + script)
