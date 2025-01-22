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
import rich
from pathlib import Path
import simbricks.utils.load_mod as load_mod
from typer import Typer, Argument, Option
from typing_extensions import Annotated
from simbricks.client.provider import client_provider
from simbricks.client.opus import base as opus_base
from ..utils import async_cli, print_table_generic


app = Typer(help="Managing SimBricks runs.")


@app.command()
@async_cli()
async def ls():
    """List runs."""
    runs = await client_provider.simbricks_client.get_runs()
    print_table_generic("Runs", runs, "id", "instantiation_id", "state")


@app.command()
@async_cli()
async def show(run_id: int):
    """Show individual run."""
    run = await client_provider.simbricks_client.get_run(run_id)
    print_table_generic("Run", [run], "id", "instantiation_id", "state")


@app.command()
@async_cli()
async def follow(run_id: int):
    """Follow individual run as it executes."""
    await opus_base.follow_run(run_id=run_id)


@app.command()
@async_cli()
async def run_con(run_id: int):
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
async def delete(run_id: int):
    """Delete an individual run."""
    client = client_provider.simbricks_client
    await client.delete_run(run_id)


@app.command()
@async_cli()
async def set_in_tar(run_id: int, source_file: str):
    """Set the tarball input for an individual run."""
    client = client_provider.simbricks_client
    await client.set_run_input(run_id, source_file)


@app.command()
@async_cli()
async def set_art(run_id: int, source_file: str):
    """Set the tarball input for an individual run."""
    client = client_provider.simbricks_client
    await client.set_run_artifact(run_id, source_file)


@app.command()
@async_cli()
async def get_art(run_id: int, destination_file: str):
    """Follow individual run as it executes."""
    client = client_provider.simbricks_client
    await client.get_run_artifact(run_id, destination_file)


@app.command()
@async_cli()
async def update(run_id: int, updates: str):
    """Update run with the 'updates' json string."""
    client = client_provider.simbricks_client
    json_updates = json.loads(updates)
    await client.update_run(run_id, updates=json_updates)


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
    input: Annotated[
        str | None,
        Option(
            "--input",
            "-i",
            help="Specify a tarball file of inputs needed for running the simulation.",
        ),
    ] = None,
):
    """Submit a SimBricks python simulation script to run."""

    system_client = client_provider.simbricks_client

    experiment_mod = load_mod.load_module(module_path=path)
    instantiations = experiment_mod.instantiations

    run_id = None
    for sb_inst in instantiations:
        run_id = await opus_base.create_run(instantiation=sb_inst)
        run = await client_provider.simbricks_client.get_run(run_id=run_id)
        print_table_generic("Run", [run], "id", "instantiation_id", "state")
        if input:
            await system_client.set_run_input(run_id, input)

    if follow and len(instantiations) > 1:
        print("Won't follow execution as more than one run was submitted.")
    elif follow and run_id:
        await opus_base.follow_run(run_id=run_id)
