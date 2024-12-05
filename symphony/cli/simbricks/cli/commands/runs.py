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

import asyncio
from pathlib import Path
import simbricks.utils.load_mod as load_mod
from typer import Typer, Argument, Option
from typing_extensions import Annotated
from ..state import state
from ..utils import async_cli

from rich.console import Console
from rich.table import Table

app = Typer(
    help="Managing SimBricks runs."
)

@app.command()
@async_cli()
async def ls():
    """List runs."""
    runs = await state.simbricks_client.get_runs()

    table = Table()
    table.add_column('Id')
    table.add_column('Instantiation')
    table.add_column('State')
    for r in runs:
        table.add_row(str(r['id']), str(r['instantiation_id']),
            r['state'])

    console = Console()
    console.print(table)

@app.command()
@async_cli()
async def show(run_id: int):
    """Show individual run."""
    run = await state.simbricks_client.get_run(run_id)
    print(run)

async def follow_run(run_id: int):
    last_run = None
    while True:
        run = await state.simbricks_client.get_run(run_id)
        if not last_run or last_run['state'] != run['state']:
            print(f'State:', run['state'])
        if not last_run or (
                len(last_run['output']) != len(run['output']) and
                len(run['output']) != 0):
            prev_len = len(last_run['output']) if last_run else 0
            print(run['output'][prev_len:])
        if run['state'] != 'pending' and run['state'] != 'running':
            break

        last_run = run
        await asyncio.sleep(1)

@app.command()
@async_cli()
async def follow(run_id: int):
    """Follow individual run as it executes."""
    await follow_run(run_id)

@app.command()
@async_cli()
async def submit_script(
    path: Annotated[Path, Argument(help="Python simulation script to submit.")],
    follow: Annotated[bool, Option("--follow", "-f",
        help="Wait for run to terminate and show output live.")] = False,

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
    print(run)

    if follow:
        await follow_run(run['id'])