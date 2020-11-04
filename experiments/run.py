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
parser.add_argument('--runs', metavar='N', type=int, default=1,
        help='Number of repetition for each experiment')

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

args = parser.parse_args()

experiments = []
for path in args.experiments:
    modname, modext = os.path.splitext(os.path.basename(path))

    if modext == '.py':
        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        experiments += mod.experiments
    else:
        with open(path, 'rb') as f:
            experiments.append(pickle.load(f))

mkdir_if_not_exists(args.workdir)
mkdir_if_not_exists(args.outdir)

if args.runtime == 'parallel':
    rt = runtime.LocalParallelRuntime(cores=args.cores, mem=args.mem)
else:
    rt = runtime.LocalSimpleRuntime()

for e in experiments:
    workdir_base = '%s/%s' % (args.workdir, e.name)
    mkdir_if_not_exists(workdir_base)

    for run in range(0, args.runs):
        outpath = '%s/%s-%d.json' % (args.outdir, e.name, run)
        if os.path.exists(outpath):
            print('skip %s run %d' % (e.name, run))
            continue

        workdir = '%s/%d' % (workdir_base, run)
        mkdir_if_not_exists(workdir)

        env = exp.ExpEnv(args.repo, workdir)
        rt.add_run(runtime.Run(e, env, outpath))

rt.start()
