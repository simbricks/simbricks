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
import asyncio
from pathlib import Path
import simbricks.utils.load_mod as load_mod
from typer import Typer, Argument, Option
from typing_extensions import Annotated
from ..state import state
from ..utils import async_cli

from rich.console import Console
from rich.table import Table

app = Typer(help="Managing SimBricks runs.")


@app.command()
@async_cli()
async def ls():
    """List runs."""
    runs = await state.simbricks_client.get_runs()

    table = Table()
    table.add_column("Id")
    table.add_column("Instantiation")
    table.add_column("State")
    for r in runs:
        table.add_row(str(r["id"]), str(r["instantiation_id"]), r["state"])

    console = Console()
    console.print(table)


@app.command()
@async_cli()
async def show(run_id: int):
    """Show individual run."""
    run = await state.simbricks_client.get_run(run_id)
    print(run)


@app.command()
@async_cli()
async def follow(run_id: int):
    """Follow individual run as it executes."""
    client = state.simbricks_client
    await client.follow_run(run_id)


@app.command()
@async_cli()
async def delete(run_id: int):
    """Delete an individual run."""
    client = state.simbricks_client
    await client.delete_run(run_id)


@app.command()
@async_cli()
async def set_input_tarball(run_id: int, source_file: str):
    """Set the tarball input for an individual run."""
    client = state.simbricks_client
    await client.set_run_input(run_id, source_file)


@app.command()
@async_cli()
async def set_output_artifact(run_id: int, source_file: str):
    """Set the tarball input for an individual run."""
    client = state.simbricks_client
    await client.set_run_artifact(run_id, source_file)


@app.command()
@async_cli()
async def get_output_artifact(run_id: int, destination_file: str):
    """Follow individual run as it executes."""
    client = state.simbricks_client
    await client.get_run_artifact(run_id, destination_file)


@app.command()
@async_cli()
async def update_run(run_id: int, updates: str):
    """Update run with the 'updates' json string."""
    client = state.simbricks_client
    json_updates = json.loads(updates)
    await client.update_run(run_id, updates=json_updates)


@app.command()
@async_cli()
async def submit_script(
    path: Annotated[Path, Argument(help="Python simulation script to submit.")],
    follow: Annotated[bool, Option("--follow", "-f", help="Wait for run to terminate and show output live.")] = False,
    input: Annotated[
        str | None, Option("--input", "-i", help="Specify a tarball file of inputs needed for running the simulation.")
    ] = None,
):
    """Submit a SimBricks python simulation script to run."""

    system_client = state.simbricks_client

    experiment_mod = load_mod.load_module(module_path=path)
    instantiations = experiment_mod.instantiations

    sb_inst = instantiations[0]
    sb_simulation = sb_inst.simulation
    sb_system = sb_simulation.system

    system = await system_client.create_system(sb_system)
    system_id = int(system["id"])
    system = await system_client.get_system(system_id)
    print(system)
    systems = await system_client.get_systems()
    print(systems)

    simulation = await system_client.create_simulation(system_id, sb_simulation)
    sim_id = int(simulation["id"])
    simulation = await system_client.get_simulation(sim_id)
    print(simulation)
    simulations = await system_client.get_simulations()
    print(simulations)

    instantiation = await system_client.create_instantiation(sim_id, None)
    inst_id = int(instantiation["id"])

    run = await system_client.create_run(inst_id)
    run_id = run["id"]
    if input:
        await system_client.set_run_input(run_id, input)
    await system_client.update_run(run_id, {"state": "pending", "output": ""})

    print(run)

    if follow:
        await system_client.follow_run(run_id)
