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

from simbricks.orchestration import exectools
from simbricks.orchestration.experiment import experiment_environment

from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.simulation import output
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.runtime_new import runs
from simbricks.orchestration.runtime_new import command_executor
from simbricks.orchestration.runtime_new import simulation_executor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    # general arguments for experiments
    parser.add_argument(
        "experiments",
        metavar="EXP",
        type=str,
        nargs="+",
        help="Python modules to load the experiments from",
    )
    parser.add_argument(
        "--list",
        action="store_const",
        const=True,
        default=False,
        help="List available experiment names",
    )
    parser.add_argument(
        "--filter",
        metavar="PATTERN",
        type=str,
        nargs="+",
        help="Only run experiments matching the given Unix shell style patterns",
    )
    parser.add_argument(
        "--pickled",
        action="store_const",
        const=True,
        default=False,
        help="Interpret experiment modules as pickled runs instead of .py files",
    )
    parser.add_argument(
        "--runs",
        metavar="N",
        type=int,
        default=1,
        help="Number of repetition of each experiment",
    )
    parser.add_argument(
        "--firstrun", metavar="N", type=int, default=1, help="ID for first run"
    )
    parser.add_argument(
        "--force",
        action="store_const",
        const=True,
        default=False,
        help="Run experiments even if output already exists (overwrites output)",
    )
    parser.add_argument(
        "--verbose",
        action="store_const",
        const=True,
        default=False,
        help="Verbose output, for example, print component simulators' output",
    )
    parser.add_argument(
        "--pcap",
        action="store_const",
        const=True,
        default=False,
        help="Dump pcap file (if supported by component simulator)",
    )
    parser.add_argument(
        "--profile-int",
        metavar="S",
        type=int,
        default=None,
        help="Enable periodic sigusr1 to each simulator every S seconds.",
    )

    # arguments for the experiment environment
    g_env = parser.add_argument_group("Environment")
    g_env.add_argument(
        "--repo",
        metavar="DIR",
        type=str,
        default=os.path.dirname(__file__) + "/..",
        help="SimBricks repository directory",
    )
    g_env.add_argument(
        "--workdir",
        metavar="DIR",
        type=str,
        default="./out/",
        help="Work directory base",
    )
    g_env.add_argument(
        "--outdir",
        metavar="DIR",
        type=str,
        default="./out/",
        help="Output directory base",
    )
    g_env.add_argument(
        "--cpdir",
        metavar="DIR",
        type=str,
        default="./out/",
        help="Checkpoint directory base",
    )
    g_env.add_argument(
        "--hosts",
        metavar="JSON_FILE",
        type=str,
        default=None,
        help="List of hosts to use (json)",
    )
    g_env.add_argument(
        "--shmdir",
        metavar="DIR",
        type=str,
        default=None,
        help="Shared memory directory base (workdir if not set)",
    )

    # arguments for the parallel runtime
    g_par = parser.add_argument_group("Parallel Runtime")
    g_par.add_argument(
        "--parallel",
        dest="runtime",
        action="store_const",
        const="parallel",
        default="sequential",
        help="Use parallel instead of sequential runtime",
    )
    g_par.add_argument(
        "--cores",
        metavar="N",
        type=int,
        default=len(os.sched_getaffinity(0)),
        help="Number of cores to use for parallel runs",
    )
    g_par.add_argument(
        "--mem",
        metavar="N",
        type=int,
        default=None,
        help="Memory limit for parallel runs (in MB)",
    )

    # arguments for the slurm runtime
    g_slurm = parser.add_argument_group("Slurm Runtime")
    g_slurm.add_argument(
        "--slurm",
        dest="runtime",
        action="store_const",
        const="slurm",
        default="sequential",
        help="Use slurm instead of sequential runtime",
    )
    g_slurm.add_argument(
        "--slurmdir",
        metavar="DIR",
        type=str,
        default="./slurm/",
        help="Slurm communication directory",
    )

    # arguments for the distributed runtime
    g_dist = parser.add_argument_group("Distributed Runtime")
    g_dist.add_argument(
        "--dist",
        dest="runtime",
        action="store_const",
        const="dist",
        default="sequential",
        help="Use sequential distributed runtime instead of local",
    )
    g_dist.add_argument(
        "--auto-dist",
        action="store_const",
        const=True,
        default=False,
        help="Automatically distribute non-distributed experiments",
    )
    g_dist.add_argument(
        "--proxy-type",
        metavar="TYPE",
        type=str,
        default="sockets",
        help="Proxy type to use (sockets,rdma) for auto distribution",
    )

    return parser.parse_args()


def load_executors(path: str) -> list[exectools.Executor]:
    """Load hosts list from json file and return list of executors."""
    with open(path, "r", encoding="utf-8") as f:
        hosts = json.load(f)

        exs = []
        for h in hosts:
            if h["type"] == "local":
                ex = command_executor.LocalExecutor()
            elif h["type"] == "remote":
                ex = command_executor.RemoteExecutor(h["host"], h["workdir"])
                if "ssh_args" in h:
                    ex.ssh_extra_args += h["ssh_args"]
                if "scp_args" in h:
                    ex.scp_extra_args += h["scp_args"]
            else:
                raise RuntimeError('invalid host type "' + h["type"] + '"')
            ex.ip = h["ip"]
            exs.append(ex)
    return exs


def warn_multi_exec(executors: list[command_executor.Executor]):
    if len(executors) > 1:
        print(
            "Warning: multiple hosts specified, only using first one for now",
            file=sys.stderr,
        )


def add_exp(
    simulation: sim_base.Simulation,
    rt: runs.base.Runtime,
    run_number: int,
    prereq: runs.base.Run | None,
    create_cp: bool,
    restore_cp: bool,
    args: argparse.Namespace,
):

    outpath = f"{args.outdir}/{simulation.name}-{run_number}.json"
    if os.path.exists(outpath) and not args.force:
        print(f"skip {e.name} run {run_number}")
        return None

    workdir = f"{args.workdir}/{simulation.name}/{run_number}"
    cpdir = f"{args.workdir}/{simulation.name}/0"
    if args.shmdir is not None:
        shmdir = f"{args.shmdir}/{simulation.name}/{run_number}"

    shm_base = ""  # TODO
    if args.shmdir is not None:
        env.shm_base = os.path.abspath(shmdir)

    # TODO: user can specify output base
    output_base = ""

    tmp_sim_files = ""  # TODO

    inst_env = inst_base.InstantiationEnvironment(
        repo_path="",
        workdir=workdir,
        cpdir=cpdir,
        create_cp=create_cp,
        restore_cp=restore_cp,
        shm_base=shm_base,
        output_base=output_base,
        tmp_simulation_files=tmp_sim_files,
    )

    inst_ = inst_base.Instantiation(inst_env)    
    output_ = output.SimulationOutput(simulation) 
    run = runs.base.Run(
        simulation=simulation,
        instantiation=inst_,
        prereq=prereq,
        output = output_
    )

    rt.add_run(run)

    return run


def main():
    args = parse_args()
    if args.hosts is None:
        executors = [command_executor.LocalExecutor()]
    else:
        executors = load_executors(args.hosts)

    # initialize runtime
    if args.runtime == "parallel":
        warn_multi_exec(executors)
        rt = runs.LocalParallelRuntime(
            cores=args.cores, mem=args.mem, verbose=args.verbose, executor=executors[0]
        )
    elif args.runtime == "slurm":
        rt = runs.SlurmRuntime(args.slurmdir, args, verbose=args.verbose)
    elif args.runtime == "dist":
        rt = runs.DistributedSimpleRuntime(executors, verbose=args.verbose)
    else:
        warn_multi_exec(executors)
        rt = runs.LocalSimpleRuntime(verbose=args.verbose, executor=executors[0])

    if args.profile_int:
        rt.enable_profiler(args.profile_int)

    # load experiments
    if not args.pickled:
        # default: load python modules with experiments
        simulations: list[sim_base.Simulation] = []
        for path in args.experiments:
            modname, _ = os.path.splitext(os.path.basename(path))

            class ExperimentModuleLoadError(Exception):
                pass

            spec = importlib.util.spec_from_file_location(modname, path)
            if spec is None:
                raise ExperimentModuleLoadError("spec is None")
            mod = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                raise ExperimentModuleLoadError("spec.loader is None")
            spec.loader.exec_module(mod)
            simulations += mod.experiments

        if args.list:
            for sim in simulations:
                print(sim.name)
            sys.exit(0)

        for sim in simulations:
            # TODO: do we want a sitributed SImulation class? --> probably not, choose slightly different abstraction
            if args.auto_dist and not isinstance(sim, sim_base.DistributedExperiment):
                sim = runs.auto_dist(sim, executors, args.proxy_type)

            # apply filter if any specified
            if (args.filter) and (len(args.filter) > 0):
                match = False
                for f in args.filter:
                    match = fnmatch.fnmatch(sim.name, f)
                    if match:
                        break

                if not match:
                    continue

            # if this is an experiment with a checkpoint we might have to create
            # it
            # TODO: what to do / how to handel checkpointing
            if sim.checkpoint:
                prereq = add_exp(sim, rt, 0, None, True, False, args)
            else:
                prereq = None

            for run in range(args.firstrun, args.firstrun + args.runs):
                add_exp(sim, rt, run, prereq, False, sim.checkpoint, args)
    else:
        # otherwise load pickled run object
        for path in args.experiments:
            with open(path, "rb") as f:
                rt.add_run(pickle.load(f))

    # register interrupt handler
    signal.signal(signal.SIGINT, lambda *_: rt.interrupt())

    # invoke runtime to run experiments
    asyncio.run(rt.start())


if __name__ == "__main__":
    main()
