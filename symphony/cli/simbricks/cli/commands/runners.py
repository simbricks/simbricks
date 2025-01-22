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

from typer import Typer, Option
from typing_extensions import Annotated
from simbricks.client.provider import client_provider
from ..utils import async_cli, print_table_generic


app = Typer(
    help="Managing SimBricks runners."
)


@app.command()
@async_cli()
async def ls():
    """List runners."""
    runners = await client_provider.runner_client(-1).list_runners()
    print_table_generic(
        "Runners", runners, "id", "label", "tags", "namespace_id", "resource_group_id"
    )


@app.command()
@async_cli()
async def show(runner_id: int):
    """Show individual runner."""
    runner = await client_provider.runner_client(runner_id).get_runner()
    print_table_generic(
        "Runners", [runner], "id", "label", "tags", "namespace_id", "resource_group_id"
    )


@app.command()
@async_cli()
async def delete(runner_id: int):
    """Delete an individual runner."""
    await client_provider.runner_client(runner_id).delete_runner()


@app.command()
@async_cli()
async def create(resource_group_id: int, label: str, tags: list[str]):
    """Update a runner with the the given label and tags."""
    runner = await client_provider.runner_client(-1).create_runner(
        resource_group_id=resource_group_id, label=label, tags=tags
    )
    print_table_generic(
        "Runner", [runner], "id", "label", "tags", "namespace_id", "resource_group_id"
    )


@app.command()
@async_cli()
async def create_event(
    runner_id: int,
    action: str,
    run_id: Annotated[int | None, Option("--run", "-r", help="Set event for specific run.")] = None,
):
    """Send a run related event to a runner (Available actions: kill (reuires a run id that shall be killed), heartbeat, simulation_status)."""
    if action == "kill" and not run_id:
        raise Exception("when trying to create a kill action you must specify a run id")
    event = await client_provider.runner_client(runner_id).create_runner_event(
        action=action, run_id=run_id
    )
    print_table_generic("Event", [event], "id", "runner_id", "action", "run_id", "event_status")


@app.command()
@async_cli()
async def delete_event(runner_id: int, event_id: int):
    """Delete a runner event."""
    await client_provider.runner_client(runner_id).delete_runner_event(event_id=event_id)


@app.command()
@async_cli()
async def update_event(
    event_id: int,
    runner_id: int,
    action: Annotated[
        str | None,
        Option(
            "--action", "-a", help="Action to set (kill, heartbeat, simulation_status, start_run)."
        ),
    ] = None,
    event_status: Annotated[
        str | None, Option("--status", "-s", help="Status to set (pending, completed, cancelled).")
    ] = None,
    run_id: Annotated[int | None, Option("--run", "-r", help="Run to set.")] = None,
):
    """Update a runner event."""
    event = await client_provider.runner_client(runner_id).update_runner_event(
        event_id=event_id, action=action, event_status=event_status, run_id=run_id
    )
    print_table_generic("Event", [event], "id", "runner_id", "action", "run_id", "event_status")


@app.command()
@async_cli()
async def ls_events(
    runner_id: int,
    action: Annotated[str | None, Option("--action", "-a", help="Filter for action.")] = None,
    event_status: Annotated[str | None, Option("--status", "-s", help="Filter for status.")] = None,
    run_id: Annotated[int | None, Option("--run", "-r", help="Filter for run.")] = None,
    limit: Annotated[int | None, Option("--limit", "-l", help="Limit results.")] = None,
):
    """List runner related events"""
    events = await client_provider.runner_client(runner_id).get_events(
        action=action, run_id=run_id, event_status=event_status, limit=limit
    )
    print_table_generic("Events", events, "id", "runner_id", "action", "run_id", "event_status")
