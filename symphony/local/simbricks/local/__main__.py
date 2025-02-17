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
users interact with for running simulations locally."""

import argparse
import asyncio
import fnmatch
import importlib
import importlib.util
import os
import pathlib
import signal
import sys

from simbricks.orchestration.instantiation import base as inst_base
from simbricks.runtime import output as sim_out
from simbricks.runtime.runs import base as runs_base
from simbricks.runtime.runs import local as rt_local
from simbricks.utils import file as utils_file


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
        "--runs",
        metavar="N",
        type=int,
        default=1,
        help="Number of repetition of each experiment",
    )
    parser.add_argument("--firstrun", metavar="N", type=int, default=1, help="ID for first run")
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
        type=pathlib.Path,
        default=pathlib.Path("/simbricks"),
        help="SimBricks repository directory",
    )
    g_env.add_argument(
        "--workdir",
        metavar="DIR",
        type=pathlib.Path,
        default=pathlib.Path("./out/"),
        help="Work directory base",
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

    return parser.parse_args()


def add_exp(
    instantiation: inst_base.Instantiation,
    prereq: runs_base.Run | None,
    rt: runs_base.Runtime,
    args: argparse.Namespace,
) -> runs_base.Run:
    workdir = utils_file.join_paths(
        args.workdir, f"{instantiation.simulation.name}/{instantiation.id()}"
    )
    env = inst_base.InstantiationEnvironment(workdir, args.repo)
    instantiation.env = env

    output = sim_out.SimulationOutput(instantiation.simulation)
    run = runs_base.Run(instantiation=instantiation, prereq=prereq, output=output)
    rt.add_run(run)
    return run


def main():
    args = parse_args()

    # initialize runtime
    if args.runtime == "parallel":
        rt = rt_local.LocalParallelRuntime(cores=args.cores, mem=args.mem, verbose=args.verbose)
    else:
        rt = rt_local.LocalSimpleRuntime(verbose=args.verbose)

    if args.profile_int:
        rt.enable_profiler(args.profile_int)

    # load python modules with experiments
    instantiations: list[inst_base.Instantiation] = []
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
        instantiations += mod.instantiations

    if args.list:
        for inst in instantiations:
            print(inst.simulation.name)
        sys.exit(0)

    for inst in instantiations:
        # if args.auto_dist and not isinstance(sim, sim_base.DistributedExperiment):
        #     sim = runs_base.auto_dist(sim, executors, args.proxy_type)

        # apply filter if any specified
        if (args.filter) and (len(args.filter) > 0):
            match = False
            for f in args.filter:
                match = fnmatch.fnmatch(inst.simulation.name, f)
                if match:
                    break

            if not match:
                continue

        inst.finalize_validate()

        # if this is an experiment with a checkpoint we might have to create
        # it
        prereq = None
        if inst.create_checkpoint and inst.simulation.any_supports_checkpointing():
            checkpointing_inst = inst.copy()
            checkpointing_inst.restore_checkpoint = False
            checkpointing_inst.create_checkpoint = True
            inst.create_checkpoint = False
            inst.restore_checkpoint = True

            prereq = add_exp(instantiation=checkpointing_inst, rt=rt, prereq=None, args=args)

        for index in range(args.firstrun, args.firstrun + args.runs):
            inst_copy = inst.copy()
            inst_copy.preserve_tmp_folder = False
            if index == args.firstrun + args.runs - 1:
                inst_copy._preserve_checkpoints = False
            add_exp(instantiation=inst_copy, rt=rt, prereq=prereq, args=args)

    # register interrupt handler
    signal.signal(signal.SIGINT, lambda *_: rt.interrupt())

    # invoke runtime to run experiments
    asyncio.run(rt.start())


if __name__ == "__main__":
    main()
