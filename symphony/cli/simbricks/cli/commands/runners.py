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
from ..utils import async_cli, print_table_generic
from ..settings import runner_client

app = Typer(help="Managing SimBricks runners.")


@app.command()
@async_cli()
async def ls():
    """List runners."""
    rc = await runner_client("undefined")
    runners = await rc.list_runners()
    print_table_generic(
        "Runners",
        runners.data,
        "id",
        "label",
        "tags",
        "plugin_tags",
        "namespace_id",
        "resource_group_id",
        "status",
    )


@app.command()
@async_cli()
async def show(runner_id: str):
    """Show individual runner."""
    rc = await runner_client(runner_id)
    runner = await rc.get_runner()
    print_table_generic(
        "Runners", [runner], "id", "label", "tags", "namespace_id", "resource_group_id", "status"
    )


@app.command()
@async_cli()
async def rm(runner_id: str):
    """Delete an individual runner."""
    rc = await runner_client(runner_id)
    await rc.delete_runner()


@app.command()
@async_cli()
async def create(resource_group_id: str, label: str, tags: list[str]):
    """Update a runner with the the given label and tags."""
    rc = await runner_client("undefined")
    runner = await rc.create_runner(
        resource_group_id, label, tags
    )
    print_table_generic(
        "Runner", [runner], "id", "label", "tags", "namespace_id", "resource_group_id", "status"
    )


@app.command()
@async_cli()
async def rm_event(runner_id: str, event_id: str):
    """Delete all events to runner up to and including the specified event."""
    rc = await runner_client(runner_id)
    await rc.delete_retrieved_events_until_event(event_id)


@app.command()
@async_cli()
async def ls_events(
    runner_id: str,
    limit: Annotated[int | None, Option("--limit", "-l", help="Limit results.")] = None,
):
    """List events going from backend to runner."""
    rc = await runner_client(runner_id)
    events = await rc.retrieve_events(limit=limit)  # TODO: add missing parameters

    print_table_generic("Events", events.data, "id", "__class__", "produced_at")
