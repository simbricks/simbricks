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
from typer import Argument, Option, Typer
from typing_extensions import Annotated

import simbricks.utils.load_mod as load_mod
from simbricks.client.opus import base as opus_base
from simbricks.client.provider import client_provider
from simbricks.schemas import base as schemas

from ..utils import async_cli, print_table_generic

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base


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
async def ls_rf(run_id: Annotated[int, Argument(help="The run id.")]):
    """List all run fragments of a run."""
    run_fragments = await client_provider.simbricks_client.get_all_run_fragments(run_id)
    print_table_generic(
        "Run Fragments",
        run_fragments,
        "id",
        "run_id",
        "runner_id",
        "state",
        "output_artifact_exists",
    )


@app.command()
@async_cli()
async def delete(run_id: int):
    """Delete an individual run."""
    client = client_provider.simbricks_client
    await client.delete_run(run_id)


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
):
    """Submit a SimBricks python simulation script to run."""

    experiment_mod = load_mod.load_module(module_path=path)
    instantiations: list[inst_base.Instantiation] = experiment_mod.instantiations

    run_id = None
    for sb_inst in instantiations:
        sb_inst.finalize_validate()
        run_id = await opus_base.create_run(instantiation=sb_inst)
        run = await client_provider.simbricks_client.get_run(run_id=run_id)
        assert run_id == run.id
        print_table_generic("Run", [run], "id", "instantiation_id", "state")

    if follow and len(instantiations) > 1:
        print("Won't follow execution as more than one run was submitted.")
    elif follow and run_id:
        await opus_base.follow_run(run_id=run_id)


@app.command()
@async_cli()
async def create(
    instantiation_id: int,
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
    run = await client_provider.simbricks_client.create_run(instantiation_id)
    print_table_generic("Run", [run], "id", "instantiation_id", "state")

    if follow and run.id is not None:
        await opus_base.follow_run(run_id=run.id)


@app.command()
@async_cli()
async def create_event(
    runner_id: int,
    run_id: int,
    run_event_type: Annotated[
        schemas.RunEventType,
        Argument(help="the event type to create (kill, simulation_status, start_run)."),
    ],
):
    """Send a heartbeat event to a runner."""

    to_create = schemas.ApiRunEventCreate(
        runner_id=runner_id,
        run_id=run_id,
        event_status=schemas.ApiEventStatus.PENDING,
        run_event_type=run_event_type,
    )
    bundle = schemas.ApiEventBundle[schemas.ApiEventCreate_U]()
    bundle.add_events(to_create)

    result_bundle = await client_provider.runner_client(runner_id).create_events(bundle)

    print_table_generic(
        "Event",
        result_bundle.events["ApiRunEventRead"],
        "id",
        "run_id",
        "runner_id",
        "event_status",
        "run_event_type",
    )


@app.command()
@async_cli()
async def delete_event(runner_id: int, run_id: int, event_id: int):
    """Delete a runner event."""

    to_delete = schemas.ApiRunEventDelete(id=event_id, runner_id=runner_id, run_id=run_id)
    bundle = schemas.ApiEventBundle[schemas.ApiRunEventDelete]()
    bundle.add_event(to_delete)

    await client_provider.runner_client(runner_id).delete_events(bundle)


@app.command()
@async_cli()
async def update_event(
    event_id: int,
    runner_id: int,
    run_id: int,
    run_event_type: Annotated[
        schemas.RunEventType,
        Argument(help="the event type to create (kill, simulation_status, start_run)."),
    ],
    event_status: Annotated[
        schemas.ApiEventStatus | None,
        Option("--status", "-s", help="Status to set (PENDING, COMPLETED, CANCELLED, ERROR)."),
    ] = None,
):
    """Update a runner event."""

    to_update = schemas.ApiRunEventUpdate(
        id=event_id, runner_id=runner_id, run_id=run_id, run_event_type=run_event_type
    )
    if event_status:
        to_update.event_status = event_status
    bundle = schemas.ApiEventBundle[schemas.ApiRunEventUpdate]()
    bundle.add_event(to_update)

    event_bundle = await client_provider.runner_client(runner_id).update_events(bundle)

    print_table_generic(
        "Events",
        event_bundle.events["ApiRunEventRead"],
        "id",
        "run_id",
        "runner_id",
        "event_status",
        "run_event_type",
    )


@app.command()
@async_cli()
async def ls_events(
    runner_id: int,
    run_id: Annotated[int | None, Option("--run", "-r", help="The run id the events belong to.")] = None,
    id: Annotated[
        int | None, Option("--ident", "-i", help="A specific event id to filter for.")
    ] = None,
    status: Annotated[
        schemas.ApiEventStatus | None,
        Option("--status", "-s", help="Filter for status (PENDING, CANCELLED, ERROR)."),
    ] = None,
    type: Annotated[
        schemas.RunEventType | None,
        Option(
            "--type", "-t", help="the event type to create (kill, simulation_status, start_run)."
        ),
    ] = None,
    limit: Annotated[int | None, Option("--limit", "-l", help="Limit results.")] = None,
):
    """List runner related events"""
    query = schemas.ApiRunEventQuery(runner_ids=[runner_id])
    if id:
        query.ids = [id]
    if run_id:
        query.run_ids = [run_id]
    if status:
        query.event_status = [status]
    if type:
        query.run_event_type = [type]
    if limit:
        query.limit = limit

    rc = client_provider.runner_client(runner_id)
    events = await opus_base.fetch_events(rc, query, schemas.ApiRunEventRead)

    print_table_generic(
        "Events",
        events,
        "id",
        "run_id",
        "runner_id",
        "event_status",
        "run_event_type",
    )
