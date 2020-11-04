import argparse
import sys
import os
import importlib
import pickle
import modes.experiments as exp
import modes.runtime as runtime

def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        os.mkdir(path)


parser = argparse.ArgumentParser()
parser.add_argument('experiments', metavar='EXP', type=str, nargs='+',
        help='An experiment file to run')
parser.add_argument('--pickled', action='store_const', const=True,
        default=False,
        help='Read exp files as pickled runs instead of exp.py files')
parser.add_argument('--runs', metavar='N', type=int, default=1,
        help='Number of repetition for each experiment')
parser.add_argument('--firstrun', metavar='N', type=int, default=1,
        help='ID for first run')
parser.add_argument('--verbose', action='store_const', const=True,
        default=False,
        help='Verbose output')

g_env = parser.add_argument_group('Environment')
g_env.add_argument('--repo', metavar='DIR', type=str,
        default='..', help='Repo directory')
g_env.add_argument('--workdir', metavar='DIR', type=str,
        default='./out/', help='Work directory base')
g_env.add_argument('--outdir', metavar='DIR',  type=str,
        default='./out/', help='Output directory base')

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
    if os.path.exists(outpath):
        print('skip %s run %d' % (e.name, run))
        return None

    workdir = '%s/%s/%d' % (args.workdir, e.name, run)

    env = exp.ExpEnv(args.repo, workdir)
    env.create_cp = create_cp
    env.restore_cp = restore_cp

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
