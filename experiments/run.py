import argparse
import sys
import os
import importlib
import pickle
import modes.experiments as exp

def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        os.mkdir(path)

parser = argparse.ArgumentParser()
parser.add_argument('experiments', metavar='EXP', type=str, nargs='+',
        help='An experiment file to run')
parser.add_argument('--runs', metavar='N', type=int, default=1,
        help='Number of runs')
parser.add_argument('--repo', metavar='DIR', type=str,
        default='..', help='Repo directory')
parser.add_argument('--workdir', metavar='DIR', type=str,
        default='./out/', help='Work directory base')
parser.add_argument('--outdir', metavar='DIR',  type=str,
        default='./out/', help='Output directory base')

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
        out = exp.run_exp_local(e, env)

        with open(outpath, 'w') as f:
            f.write(out.dumps())
