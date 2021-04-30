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

import argparse
import sys
import os
import importlib
import importlib.util
import pickle
import fnmatch
import simbricks.experiments as exp
import simbricks.runtime as runtime

def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        os.mkdir(path)


parser = argparse.ArgumentParser()
parser.add_argument('experiments', metavar='EXP', type=str, nargs='+',
        help='An experiment file to run')
parser.add_argument('--filter', metavar='PATTERN', type=str, nargs='+',
        help='Pattern to match experiment names against')
parser.add_argument('--pickled', action='store_const', const=True,
        default=False,
        help='Read exp files as pickled runs instead of exp.py files')
parser.add_argument('--runs', metavar='N', type=int, default=1,
        help='Number of repetition for each experiment')
parser.add_argument('--firstrun', metavar='N', type=int, default=1,
        help='ID for first run')
parser.add_argument('--force', action='store_const', const=True, default=False,
        help='Run experiments even if output already exists')
parser.add_argument('--verbose', action='store_const', const=True,
        default=False,
        help='Verbose output')
parser.add_argument('--pcap', action='store_const', const=True, default=False,
        help='Dump pcap file (if supported by simulator)')

g_env = parser.add_argument_group('Environment')
g_env.add_argument('--repo', metavar='DIR', type=str,
        default='..', help='Repo directory')
g_env.add_argument('--workdir', metavar='DIR', type=str,
        default='./out/', help='Work directory base')
g_env.add_argument('--outdir', metavar='DIR',  type=str,
        default='./out/', help='Output directory base')
g_env.add_argument('--cpdir', metavar='DIR',  type=str,
        default='./out/', help='Checkpoint directory base')

g_par = parser.add_argument_group('Parallel Runtime')
g_par.add_argument('--parallel', dest='runtime', action='store_const',
        const='parallel', default='sequential',
        help='Use parallel instead of sequential runtime')
g_par.add_argument('--cores', metavar='N', type=int,
        default=len(os.sched_getaffinity(0)),
        help='Number of cores to use for parallel runs')
g_par.add_argument('--mem', metavar='N', type=int, default=None,
        help='Memory limit for parallel runs (in MB)')

g_slurm = parser.add_argument_group('Slurm Runtime')
g_slurm.add_argument('--slurm', dest='runtime', action='store_const',
        const='slurm', default='sequential',
        help='Use slurm instead of sequential runtime')
g_slurm.add_argument('--slurmdir', metavar='DIR',  type=str,
        default='./slurm/', help='Slurm communication directory')


args = parser.parse_args()

# initialize runtime
if args.runtime == 'parallel':
    rt = runtime.LocalParallelRuntime(cores=args.cores, mem=args.mem,
            verbose=args.verbose)
elif args.runtime == 'slurm':
    rt = runtime.SlurmRuntime(args.slurmdir, args, verbose=args.verbose)
else:
    rt = runtime.LocalSimpleRuntime(verbose=args.verbose)

def add_exp(e, run, prereq, create_cp, restore_cp):
    outpath = '%s/%s-%d.json' % (args.outdir, e.name, run)
    if os.path.exists(outpath) and not args.force:
        print('skip %s run %d' % (e.name, run))
        return None

    workdir = '%s/%s/%d' % (args.workdir, e.name, run)
    cpdir = '%s/%s/%d' % (args.cpdir, e.name, 0)

    env = exp.ExpEnv(args.repo, workdir, cpdir)
    env.create_cp = create_cp
    env.restore_cp = restore_cp
    env.pcap_file = ''
    if args.pcap:
        env.pcap_file = workdir+'/pcap'

    run = runtime.Run(e, run, env, outpath, prereq)
    rt.add_run(run)
    return run

# load experiments
if not args.pickled:
    # default: load python modules with experiments
    experiments = []
    for path in args.experiments:
        modname, _ = os.path.splitext(os.path.basename(path))

        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        experiments += mod.experiments

    for e in experiments:
        # apply filter if any specified
        if (args.filter) and (len(args.filter) > 0):
            match = False
            for f in args.filter:
                if fnmatch.fnmatch(e.name, f):
                    match = True
                    break
            if not match:
                continue

        # if this is an experiment with a checkpoint we might have to create it
        if e.checkpoint:
            prereq = add_exp(e, 0, None, True, False)
        else:
            prereq = None

        for run in range(args.firstrun, args.firstrun + args.runs):
            add_exp(e, run, prereq, False, e.checkpoint)
else:
    # otherwise load pickled run object
    for path in args.experiments:
        with open(path, 'rb') as f:
            rt.add_run(pickle.load(f))

rt.start()
