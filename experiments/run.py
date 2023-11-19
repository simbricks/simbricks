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
"""This is the top-level module of the SimBricks orchestration framework that
users interact with."""

import argparse
import asyncio
import fnmatch
import importlib
import importlib.util
import json
import os
import pickle
import signal
import sys
import typing as tp

from simbricks.orchestration import exectools
from simbricks.orchestration import experiments as exps
from simbricks.orchestration import runtime
from simbricks.orchestration.experiment import experiment_environment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    # general arguments for experiments
    parser.add_argument(
        'experiments',
        metavar='EXP',
        type=str,
        nargs='+',
        help='Python modules to load the experiments from'
    )
    parser.add_argument(
        '--list',
        action='store_const',
        const=True,
        default=False,
        help='List available experiment names'
    )
    parser.add_argument(
        '--filter',
        metavar='PATTERN',
        type=str,
        nargs='+',
        help='Only run experiments matching the given Unix shell style patterns'
    )
    parser.add_argument(
        '--pickled',
        action='store_const',
        const=True,
        default=False,
        help='Interpret experiment modules as pickled runs instead of .py files'
    )
    parser.add_argument(
        '--runs',
        metavar='N',
        type=int,
        default=1,
        help='Number of repetition of each experiment'
    )
    parser.add_argument(
        '--firstrun', metavar='N', type=int, default=1, help='ID for first run'
    )
    parser.add_argument(
        '--force',
        action='store_const',
        const=True,
        default=False,
        help='Run experiments even if output already exists (overwrites output)'
    )
    parser.add_argument(
        '--verbose',
        action='store_const',
        const=True,
        default=False,
        help='Verbose output, for example, print component simulators\' output'
    )
    parser.add_argument(
        '--pcap',
        action='store_const',
        const=True,
        default=False,
        help='Dump pcap file (if supported by component simulator)'
    )

    # arguments for the experiment environment
    g_env = parser.add_argument_group('Environment')
    g_env.add_argument(
        '--repo',
        metavar='DIR',
        type=str,
        default='..',
        help='SimBricks repository directory'
    )
    g_env.add_argument(
        '--workdir',
        metavar='DIR',
        type=str,
        default='./out/',
        help='Work directory base'
    )
    g_env.add_argument(
        '--outdir',
        metavar='DIR',
        type=str,
        default='./out/',
        help='Output directory base'
    )
    g_env.add_argument(
        '--cpdir',
        metavar='DIR',
        type=str,
        default='./out/',
        help='Checkpoint directory base'
    )
    g_env.add_argument(
        '--hosts',
        metavar='JSON_FILE',
        type=str,
        default=None,
        help='List of hosts to use (json)'
    )
    g_env.add_argument(
        '--shmdir',
        metavar='DIR',
        type=str,
        default=None,
        help='Shared memory directory base (workdir if not set)'
    )

    # arguments for the parallel runtime
    g_par = parser.add_argument_group('Parallel Runtime')
    g_par.add_argument(
        '--parallel',
        dest='runtime',
        action='store_const',
        const='parallel',
        default='sequential',
        help='Use parallel instead of sequential runtime'
    )
    g_par.add_argument(
        '--cores',
        metavar='N',
        type=int,
        default=len(os.sched_getaffinity(0)),
        help='Number of cores to use for parallel runs'
    )
    g_par.add_argument(
        '--mem',
        metavar='N',
        type=int,
        default=None,
        help='Memory limit for parallel runs (in MB)'
    )

    # arguments for the slurm runtime
    g_slurm = parser.add_argument_group('Slurm Runtime')
    g_slurm.add_argument(
        '--slurm',
        dest='runtime',
        action='store_const',
        const='slurm',
        default='sequential',
        help='Use slurm instead of sequential runtime'
    )
    g_slurm.add_argument(
        '--slurmdir',
        metavar='DIR',
        type=str,
        default='./slurm/',
        help='Slurm communication directory'
    )

    # arguments for the distributed runtime
    g_dist = parser.add_argument_group('Distributed Runtime')
    g_dist.add_argument(
        '--dist',
        dest='runtime',
        action='store_const',
        const='dist',
        default='sequential',
        help='Use sequential distributed runtime instead of local'
    )
    g_dist.add_argument(
        '--auto-dist',
        action='store_const',
        const=True,
        default=False,
        help='Automatically distribute non-distributed experiments'
    )
    g_dist.add_argument(
        '--proxy-type',
        metavar='TYPE',
        type=str,
        default='sockets',
        help='Proxy type to use (sockets,rdma) for auto distribution'
    )

    return parser.parse_args()


def load_executors(path: str) -> tp.List[exectools.Executor]:
    """Load hosts list from json file and return list of executors."""
    with open(path, 'r', encoding='utf-8') as f:
        hosts = json.load(f)

        exs = []
        for h in hosts:
            if h['type'] == 'local':
                ex = exectools.LocalExecutor()
            elif h['type'] == 'remote':
                ex = exectools.RemoteExecutor(h['host'], h['workdir'])
                if 'ssh_args' in h:
                    ex.ssh_extra_args += h['ssh_args']
                if 'scp_args' in h:
                    ex.scp_extra_args += h['scp_args']
            else:
                raise RuntimeError('invalid host type "' + h['type'] + '"')
            ex.ip = h['ip']
            exs.append(ex)
    return exs


def warn_multi_exec(executors: tp.List[exectools.Executor]):
    if len(executors) > 1:
        print(
            'Warning: multiple hosts specified, only using first one for now',
            file=sys.stderr
        )


def add_exp(
    e: exps.Experiment,
    rt: runtime.Runtime,
    run: int,
    prereq: tp.Optional[runtime.Run],
    create_cp: bool,
    restore_cp: bool,
    no_simbricks: bool,
    args: argparse.Namespace
):
    outpath = f'{args.outdir}/{e.name}-{run}.json'
    if os.path.exists(outpath) and not args.force:
        print(f'skip {e.name} run {run}')
        return None

    workdir = f'{args.workdir}/{e.name}/{run}'
    cpdir = f'{args.cpdir}/{e.name}/0'
    if args.shmdir is not None:
        shmdir = f'{args.shmdir}/{e.name}/{run}'

    env = experiment_environment.ExpEnv(args.repo, workdir, cpdir)
    env.create_cp = create_cp
    env.restore_cp = restore_cp
    env.no_simbricks = no_simbricks
    env.pcap_file = ''
    if args.pcap:
        env.pcap_file = workdir + '/pcap'
    if args.shmdir is not None:
        env.shm_base = os.path.abspath(shmdir)

    run = runtime.Run(e, run, env, outpath, prereq)
    rt.add_run(run)
    return run


def main():
    args = parse_args()
    if args.hosts is None:
        executors = [exectools.LocalExecutor()]
    else:
        executors = load_executors(args.hosts)

    # initialize runtime
    if args.runtime == 'parallel':
        warn_multi_exec(executors)
        rt = runtime.LocalParallelRuntime(
            cores=args.cores,
            mem=args.mem,
            verbose=args.verbose,
            executor=executors[0]
        )
    elif args.runtime == 'slurm':
        rt = runtime.SlurmRuntime(args.slurmdir, args, verbose=args.verbose)
    elif args.runtime == 'dist':
        rt = runtime.DistributedSimpleRuntime(executors, verbose=args.verbose)
    else:
        warn_multi_exec(executors)
        rt = runtime.LocalSimpleRuntime(
            verbose=args.verbose, executor=executors[0]
        )

    # load experiments
    if not args.pickled:
        # default: load python modules with experiments
        experiments = []
        for path in args.experiments:
            modname, _ = os.path.splitext(os.path.basename(path))

            class ExperimentModuleLoadError(Exception):
                pass

            spec = importlib.util.spec_from_file_location(modname, path)
            if spec is None:
                raise ExperimentModuleLoadError('spec is None')
            mod = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                raise ExperimentModuleLoadError('spec.loader is None')
            spec.loader.exec_module(mod)
            experiments += mod.experiments

        if args.list:
            for e in experiments:
                print(e.name)
            sys.exit(0)

        for e in experiments:
            if args.auto_dist and not isinstance(e, exps.DistributedExperiment):
                e = runtime.auto_dist(e, executors, args.proxy_type)
            # apply filter if any specified
            if (args.filter) and (len(args.filter) > 0):
                match = False
                for f in args.filter:
                    match = fnmatch.fnmatch(e.name, f)
                    if match:
                        break

                if not match:
                    continue

            # if this is an experiment with a checkpoint we might have to create
            # it
            no_simbricks = e.no_simbricks
            if e.checkpoint:
                prereq = add_exp(
                    e, rt, 0, None, True, False, no_simbricks, args
                )
            else:
                prereq = None

            for run in range(args.firstrun, args.firstrun + args.runs):
                add_exp(
                    e, rt, run, prereq, False, e.checkpoint, no_simbricks, args
                )
    else:
        # otherwise load pickled run object
        for path in args.experiments:
            with open(path, 'rb') as f:
                rt.add_run(pickle.load(f))

    # register interrupt handler
    signal.signal(signal.SIGINT, lambda *_: rt.interrupt())

    # invoke runtime to run experiments
    asyncio.run(rt.start())


if __name__ == '__main__':
    main()
