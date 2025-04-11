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
from simbricks.schemas import base as schemas
from simbricks.client.opus import base as opus_base

app = Typer(help="Managing SimBricks runners.")


@app.command()
@async_cli()
async def ls():
    """List runners."""
    runners = await client_provider.runner_client(-1).list_runners()
    print_table_generic(
        "Runners", runners, "id", "label", "tags", "plugin_tags", "namespace_id", "resource_group_id", "status"
    )


@app.command()
@async_cli()
async def show(runner_id: int):
    """Show individual runner."""
    runner = await client_provider.runner_client(runner_id).get_runner()
    print_table_generic(
        "Runners", [runner], "id", "label", "tags", "namespace_id", "resource_group_id", "status"
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
        "Runner", [runner], "id", "label", "tags", "namespace_id", "resource_group_id", "status"
    )


@app.command()
@async_cli()
async def create_event(
    runner_id: int,
):
    """Send a heartbeat event to a runner."""

    to_create = schemas.ApiRunnerEventCreate(
        runner_id=runner_id,
        event_status=schemas.ApiEventStatus.PENDING,
        runner_event_type=schemas.RunnerEventType.heartbeat,
    )
    bundle = schemas.ApiEventBundle[schemas.ApiEventCreate_U]()
    bundle.add_events(to_create)

    result_bundle = await client_provider.runner_client(runner_id).create_events(bundle)

    print_table_generic(
        "Event",
        result_bundle.events["ApiRunnerEventRead"],
        "id",
        "runner_id",
        "event_status",
        "runner_event_type",
    )


@app.command()
@async_cli()
async def delete_event(runner_id: int, event_id: int):
    """Delete a runner event."""

    to_delete = schemas.ApiRunnerEventDelete(id=event_id, runner_id=runner_id)
    bundle = schemas.ApiEventBundle[schemas.ApiEventDelete_U]()
    bundle.add_event(to_delete)

    await client_provider.runner_client(runner_id).delete_events(bundle)


@app.command()
@async_cli()
async def update_event(
    event_id: int,
    runner_id: int,
    event_status: Annotated[
        schemas.ApiEventStatus | None,
        Option("--status", "-s", help="Status to set (PENDING, COMPLETED, CANCELLED, ERROR)."),
    ] = None,
):
    """Update a runner event."""

    to_update = schemas.ApiRunnerEventUpdate(id=event_id, runner_id=runner_id)
    if event_status:
        to_update.event_status = event_status
    bundle = schemas.ApiEventBundle[schemas.ApiEventUpdate_U]()
    bundle.add_event(to_update)

    event_bundle = await client_provider.runner_client(runner_id).update_events(bundle)

    print_table_generic(
        "Events",
        event_bundle.events["ApiRunnerEventRead"],
        "id",
        "runner_id",
        "event_status",
        "runner_event_type",
    )


@app.command()
@async_cli()
async def ls_events(
    runner_id: int,
    id: Annotated[
        int | None, Option("--ident", "-i", help="A specific event id to filter for.")
    ] = None,
    status: Annotated[
        schemas.ApiEventStatus | None,
        Option("--status", "-s", help="Filter for status (PENDING, CANCELLED, ERROR)."),
    ] = None,
    limit: Annotated[int | None, Option("--limit", "-l", help="Limit results.")] = None,
):
    """List runner related events"""
    query = schemas.ApiRunnerEventQuery(runner_ids=[runner_id])
    if id:
        query.ids = [id]
    if status:
        query.event_status = [status]
    if limit:
        query.limit = limit

    rc = client_provider.runner_client(runner_id)
    events = await opus_base.fetch_events(rc, query, schemas.ApiRunnerEventRead)

    print_table_generic(
        "Events",
        events,
        "id",
        "runner_id",
        "event_status",
        "runner_event_type",
    )
