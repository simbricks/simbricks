#!/usr/bin/python3

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
import asyncio
import fnmatch
import importlib
import importlib.util
import json
import os
import pickle
import sys
import typing as tp
from signal import SIGINT, signal

from simbricks.orchestration.exectools import LocalExecutor, RemoteExecutor
from simbricks.orchestration.experiment.experiment_environment import ExpEnv
from simbricks.orchestration.experiments import (
    DistributedExperiment, Experiment
)
from simbricks.orchestration.runtime.common import Run
from simbricks.orchestration.runtime.distributed import (
    DistributedSimpleRuntime, auto_dist
)
from simbricks.orchestration.runtime.local import (
    LocalParallelRuntime, LocalSimpleRuntime
)
from simbricks.orchestration.runtime.slurm import SlurmRuntime


# pylint: disable=redefined-outer-name
def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        os.mkdir(path)


parser = argparse.ArgumentParser()
parser.add_argument(
    'experiments',
    metavar='EXP',
    type=str,
    nargs='+',
    help='An experiment file to run'
)
parser.add_argument(
    '--list',
    action='store_const',
    const=True,
    default=False,
    help='Only list available experiment names'
)
parser.add_argument(
    '--filter',
    metavar='PATTERN',
    type=str,
    nargs='+',
    help='Pattern to match experiment names against'
)
parser.add_argument(
    '--pickled',
    action='store_const',
    const=True,
    default=False,
    help='Read exp files as pickled runs instead of exp.py files'
)
parser.add_argument(
    '--runs',
    metavar='N',
    type=int,
    default=1,
    help='Number of repetition for each experiment'
)
parser.add_argument(
    '--firstrun', metavar='N', type=int, default=1, help='ID for first run'
)
parser.add_argument(
    '--force',
    action='store_const',
    const=True,
    default=False,
    help='Run experiments even if output already exists'
)
parser.add_argument(
    '--verbose',
    action='store_const',
    const=True,
    default=False,
    help='Verbose output'
)
parser.add_argument(
    '--pcap',
    action='store_const',
    const=True,
    default=False,
    help='Dump pcap file (if supported by simulator)'
)

g_env = parser.add_argument_group('Environment')
g_env.add_argument(
    '--repo', metavar='DIR', type=str, default='..', help='Repo directory'
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
args = parser.parse_args()


# pylint: disable=redefined-outer-name
def load_executors(path):
    """Load hosts list from json file and return list of executors."""
    with open(path, 'r', encoding='utf-8') as f:
        hosts = json.load(f)

        exs = []
        for h in hosts:
            if h['type'] == 'local':
                ex = LocalExecutor()
            elif h['type'] == 'remote':
                ex = RemoteExecutor(h['host'], h['workdir'])
                if 'ssh_args' in h:
                    ex.ssh_extra_args += h['ssh_args']
                if 'scp_args' in h:
                    ex.scp_extra_args += h['scp_args']
            else:
                raise RuntimeError('invalid host type "' + h['type'] + '"')
            ex.ip = h['ip']
            exs.append(ex)
    return exs


if args.hosts is None:
    executors = [LocalExecutor()]
else:
    executors = load_executors(args.hosts)


def warn_multi_exec():
    if len(executors) > 1:
        print(
            'Warning: multiple hosts specified, only using first one for now',
            file=sys.stderr
        )


# initialize runtime
if args.runtime == 'parallel':
    warn_multi_exec()
    rt = LocalParallelRuntime(
        cores=args.cores,
        mem=args.mem,
        verbose=args.verbose,
        executor=executors[0]
    )
elif args.runtime == 'slurm':
    rt = SlurmRuntime(args.slurmdir, args, verbose=args.verbose)
elif args.runtime == 'dist':
    rt = DistributedSimpleRuntime(executors, verbose=args.verbose)
else:
    warn_multi_exec()
    rt = LocalSimpleRuntime(verbose=args.verbose, executor=executors[0])


# pylint: disable=redefined-outer-name
def add_exp(
    e: Experiment,
    run: int,
    prereq: tp.Optional[Run],
    create_cp: bool,
    restore_cp: bool,
    no_simbricks: bool
):
    outpath = f'{args.outdir}/{e.name}-{run}.json'
    if os.path.exists(outpath) and not args.force:
        print(f'skip {e.name} run {run}')
        return None

    workdir = f'{args.workdir}/{e.name}/{run}'
    cpdir = f'{args.cpdir}/{e.name}/0'
    if args.shmdir is not None:
        shmdir = f'{args.shmdir}/{e.name}/{run}'

    env = ExpEnv(args.repo, workdir, cpdir)
    env.create_cp = create_cp
    env.restore_cp = restore_cp
    env.no_simbricks = no_simbricks
    env.pcap_file = ''
    if args.pcap:
        env.pcap_file = workdir + '/pcap'
    if args.shmdir is not None:
        env.shm_base = os.path.abspath(shmdir)

    run = Run(e, run, env, outpath, prereq)
    rt.add_run(run)
    return run


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
        if args.auto_dist and not isinstance(e, DistributedExperiment):
            e = auto_dist(e, executors, args.proxy_type)
        # apply filter if any specified
        if (args.filter) and (len(args.filter) > 0):
            match = False
            for f in args.filter:
                match = fnmatch.fnmatch(e.name, f)
                if match:
                    break

            if not match:
                continue

        # if this is an experiment with a checkpoint we might have to create it
        no_simbricks = e.no_simbricks
        if e.checkpoint:
            prereq = add_exp(e, 0, None, True, False, no_simbricks)
        else:
            prereq = None

        for run in range(args.firstrun, args.firstrun + args.runs):
            add_exp(e, run, prereq, False, e.checkpoint, no_simbricks)
else:
    # otherwise load pickled run object
    for path in args.experiments:
        with open(path, 'rb') as f:
            rt.add_run(pickle.load(f))

# register interrupt handler
signal(SIGINT, lambda *_: rt.interrupt())

asyncio.run(rt.start())
