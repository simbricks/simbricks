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
import shutil
import signal
import sys

from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import image_cache, image_layers
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
        help=(
            "Reuse the run directories of an earlier invocation, discarding their contents"
            " (default: run in a new directory with a -1, -2, ... suffix)"
        ),
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
        "--global-input-dir",
        metavar="DIR",
        type=pathlib.Path,
        help="Global input directory",
    )
    g_env.add_argument(
        "--image-cache-dir",
        metavar="DIR",
        type=pathlib.Path,
        help=(
            "Keep built disk images here and reuse them in later runs"
            f" (default: <workdir>/{image_cache.DEFAULT_DIR_NAME})"
        ),
    )
    g_env.add_argument(
        "--no-image-cache",
        action="store_true",
        help="Do not keep built disk images at all, building and downloading them for every run",
    )
    g_env.add_argument(
        "--image-cache-size",
        metavar="SIZE",
        type=str,
        help=(
            "Keep the image cache under this size, e.g. 200G, evicting least recently used"
            f" (default: {image_cache.DEFAULT_SIZE // (1 << 30)}G for the default cache"
            " directory, unbounded for one given with --image-cache-dir)"
        ),
    )
    g_env.add_argument(
        "--image-cache-compression",
        metavar="ALGO",
        type=str,
        choices=image_cache.COMPRESSIONS,
        help=(
            "How to compress images kept in the cache (default: "
            f"{image_cache.COMPRESSION_DEFAULT}). 'none' trades cache space for"
            " a little less work reading an image back"
        ),
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


def copy_instantiation(to_copy: inst_base.Instantiation) -> inst_base.Instantiation:
    # TODO: this is an somewhat ugly hack to make a copy
    json_sys_tmp = to_copy.simulation.system.toJSON()
    json_sim_tmp = to_copy.simulation.toJSON()
    json_inst_tmp = to_copy.toJSON()
    sys_copy = sys_base.System.fromJSON(json_sys_tmp)
    sim_copy = sim_base.Simulation.fromJSON(sys_copy, json_sim_tmp)
    inst_copy = inst_base.Instantiation.fromJSON(sim_copy, json_inst_tmp)
    return inst_copy


class RunDirs:
    """Gives every run its own directory below the work directory base."""

    def __init__(self, base: pathlib.Path, force: bool) -> None:
        self._base = base
        self._force = force
        self._given_out: list[pathlib.Path] = []

    def claim(self, name: str) -> pathlib.Path:
        """`<base>/<name>`, or `<base>/<name>-N` with the smallest N that is still free.

        A directory left behind by an earlier invocation is not free, unless force is set: then
        it is deleted and used again.
        """
        wanted = pathlib.Path(utils_file.join_paths(self._base, name))

        path = wanted
        n = 1
        while not self._free(path):
            path = wanted.with_name(f"{wanted.name}-{n}")
            n += 1

        if self._force and path.exists():
            print(f"--force: removing {path}")
            shutil.rmtree(path)
        elif path != wanted:
            print(f"{wanted} already in use, running in {path}")

        path.mkdir(parents=True)
        self._given_out.append(path)
        return path

    def _free(self, path: pathlib.Path) -> bool:
        if path in self._given_out:
            return False
        return self._force or not path.exists()

    def remove_unused(self) -> None:
        """Remove the directories of runs that never started, e.g. after an interrupt."""
        for path in self._given_out:
            if not any(path.iterdir()):
                path.rmdir()


def image_cache_config(args: argparse.Namespace) -> tuple[pathlib.Path | None, int | None]:
    """Where images are kept between runs, and how large that may grow."""
    if args.no_image_cache:
        return None, None
    if args.image_cache_dir is not None:
        cache_dir = args.image_cache_dir.resolve()
        default_size = None
    else:
        cache_dir = image_cache.default_dir(args.workdir)
        default_size = image_cache.DEFAULT_SIZE
    if args.image_cache_size is None:
        return cache_dir, default_size
    return cache_dir, image_layers.parse_size(args.image_cache_size)


def add_exp(
    instantiation: inst_base.Instantiation,
    prereq: runs_base.Run | None,
    rt: runs_base.Runtime,
    args: argparse.Namespace,
    workdir: pathlib.Path,
) -> runs_base.Run:
    cache_dir, cache_size = image_cache_config(args)
    # A run depending on another run restores the checkpoint that run took.
    checkpoint_dir = pathlib.Path(prereq.instantiation.env.cp_dir()) if prereq else None
    env = inst_base.InstantiationEnvironment(
        workdir,
        args.global_input_dir,
        cache_dir,
        cache_size,
        args.image_cache_compression,
        checkpoint_dir=checkpoint_dir,
    )
    instantiation.env = env
    assert len(instantiation.fragments) == 1
    instantiation.assigned_fragment = instantiation.fragments[0]

    output = sim_out.SimulationOutput(instantiation.simulation)
    run = runs_base.Run(instantiation=instantiation, prereq=prereq, simulation_output=output)
    rt.add_run(run)
    return run


def add_runs(
    instantiations: list[inst_base.Instantiation],
    rt: runs_base.Runtime,
    run_dirs: RunDirs,
    args: argparse.Namespace,
) -> None:
    for inst in instantiations:
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

        name = f"{inst.simulation.name}/{inst.id()}"
        workdir = run_dirs.claim(name)

        # if this is an experiment with a checkpoint we might have to create
        # it
        prereq = None
        if inst.create_checkpoint and inst.simulation.any_supports_checkpointing():
            checkpointing_inst = copy_instantiation(inst)
            checkpointing_inst.restore_checkpoint = False
            checkpointing_inst.create_checkpoint = True
            inst.create_checkpoint = False
            inst.restore_checkpoint = True

            # shares the first repetition's directory
            prereq = add_exp(
                instantiation=checkpointing_inst, rt=rt, prereq=None, args=args, workdir=workdir
            )

        for index in range(args.firstrun, args.firstrun + args.runs):
            if index > args.firstrun:
                workdir = run_dirs.claim(name)
            inst_copy = copy_instantiation(inst)
            inst_copy.preserve_tmp_folder = False
            if index == args.firstrun + args.runs - 1:
                inst_copy._preserve_checkpoints = False
            add_exp(instantiation=inst_copy, rt=rt, prereq=prereq, args=args, workdir=workdir)


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

    run_dirs = RunDirs(args.workdir, args.force)
    try:
        add_runs(instantiations, rt, run_dirs, args)

        # register interrupt handler
        signal.signal(signal.SIGINT, lambda *_: rt.interrupt())

        # invoke runtime to run experiments
        asyncio.run(rt.start())
    finally:
        run_dirs.remove_unused()


if __name__ == "__main__":
    main()
