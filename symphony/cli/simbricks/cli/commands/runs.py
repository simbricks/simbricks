# Copyright 2024 Max Planck Institute for Software Systems, and
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

import json
import typing
from pathlib import Path

import rich
from aiohttp import client_exceptions
from typer import Argument, Option, Typer, Exit
from typing_extensions import Annotated

import simbricks.utils.load_mod as load_mod
from simbricks.client.opus import base as opus_base
from simbricks.client import simb_client

from ..utils import async_cli, print_table_generic

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base


app = Typer(help="Managing SimBricks runs.")


@app.command()
@async_cli()
async def ls():
    """List runs."""
    runs = await simb_client().get_runs()
    print_table_generic("Runs", runs.data, "id", "instantiation_id", "state")


@app.command()
@async_cli()
async def show(run_id: str):
    """Show individual run."""
    run = await simb_client().get_run(run_id)
    print_table_generic("Run", [run], "id", "instantiation_id", "state")


@app.command()
@async_cli()
async def follow(run_id: str):
    """Follow individual run as it executes."""
    await opus_base.follow_run(run_id=run_id)


@app.command()
@async_cli()
async def run_con(run_id: str):
    """Print a runs console completely."""
    console = rich.console.Console()
    pretty_printer = opus_base.ComponentOutputPrettyPrinter(console)
    with console.status(f"[bold green]Waiting for console output of run {run_id} ..."):
        async for prefix, line in opus_base.ConsoleLineGenerator(
            run_id=run_id, follow=False
        ).generate_lines():
            pretty_printer.print_line(prefix, line)


@app.command()
@async_cli()
async def ls_rf(run_id: Annotated[str, Argument(help="The run id.")]):
    """List all run fragments of a run."""
    run_fragments = await simb_client().get_all_run_fragments(run_id)
    print_table_generic(
        "Run Fragments",
        run_fragments.data,
        "id",
        "run_id",
        "runner_id",
        "state",
        "output_artifact_exists",
    )


@app.command()
@async_cli()
async def get_output_artifact(
    run_id: Annotated[str, Argument(help="The run id.")],
    run_fragment_id: Annotated[str, Argument(help="The run fragment id.")],
    path: Annotated[
        Path, Argument(help="The path where to store the output artifact.", writable=True)
    ] = Path("./"),
):
    """Retrieve the output artifact that is stored for a run fragment."""
    if path.is_dir():
        path = path / Path(f"output_artifact_{run_fragment_id}.zip")
    if not path.parent.exists():
        raise RuntimeError(f"The path '{path.parent}' does not exist.")

    await simb_client().get_run_fragment_output_artifact(run_id, run_fragment_id, path.as_posix())


@app.command()
@async_cli()
async def rm(run_id: str):
    """Delete an individual run."""
    await simb_client().delete_run(run_id)


@app.command()
@async_cli()
async def submit(
    path: Annotated[Path, Argument(help="Python simulation script to submit.")],
    follow: Annotated[
        bool,
        Option(
            "--follow",
            "-f",
            help="Wait for run to terminate and show output live. This only works in case a single instantiation is defined in your experiment scripts instantiations list.",
        ),
    ] = False,
):
    """Submit a SimBricks python simulation script to run."""

    experiment_mod = load_mod.load_module(module_path=path.as_posix())
    instantiations: list[inst_base.Instantiation] = experiment_mod.instantiations

    run_id = None
    for sb_inst in instantiations:
        run_id = await opus_base.create_run(instantiation=sb_inst)
        run = await simb_client().get_run(run_id)
        assert run_id == run.id
        print_table_generic("Run", [run], "id", "instantiation_id", "state")

    if follow and len(instantiations) > 1:
        print("Won't follow execution as more than one run was submitted.")
    elif follow and run_id:
        await opus_base.follow_run(run_id=run_id)


@app.command()
@async_cli()
async def create(
    inst_id: str,
    follow: Annotated[
        bool,
        Option(
            "--follow",
            "-f",
            help="Wait for run to terminate and show output live.",
        ),
    ] = False,
):
    """Create a virtual prototype run based on an already submitted configuration."""
    run = await simb_client().create_run(inst_id)
    print_table_generic("Run", [run], "id", "instantiation_id", "state")

    if follow and run.id is not None:
        await opus_base.follow_run(run_id=run.id)
