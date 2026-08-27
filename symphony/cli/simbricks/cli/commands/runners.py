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

from typer import Option, Typer
from typing_extensions import Annotated

from simbricks.client.opus import base as opus_base

from ..pager import PAGE_SIZE, PEEK_COUNT, paged_ls
from ..settings import runner_client
from ..utils import async_cli, print_table_generic

app = Typer(help="Managing SimBricks runners.")

_RUNNER_COLUMNS = (
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
async def ls(
    limit: Annotated[int, Option("--limit", "-n", help="Number of runners per page.")] = PAGE_SIZE,
    fetch_all: Annotated[
        bool,
        Option(
            "--all",
            "-a",
            help="Retrieve every runner at once instead of paging through them.",
        ),
    ] = False,
):
    """List runners.

    Pages interactively when there is more than one page and the output is a
    terminal. Left and right change page, g jumps back to the first page, r
    reloads the current one and q quits.
    """
    rc = await runner_client("undefined")
    page_limit = None if fetch_all else limit
    await paged_ls(
        "Runners",
        _RUNNER_COLUMNS,
        lambda cursor: opus_base.get_runners_page(rc, cursor_next=cursor, limit=page_limit),
    )


@app.command()
@async_cli()
async def peek(
    limit: Annotated[int, Option("--limit", "-n", help="Number of runners to peek.")] = PEEK_COUNT,
):
    """Show the most recent runners, 5 by default."""
    rc = await runner_client("undefined")
    runners, _ = await opus_base.get_runners_page(rc, limit=limit)
    print_table_generic("Latest Runners", runners, *_RUNNER_COLUMNS)


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
    runner = await rc.create_runner(resource_group_id, label, tags)
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
