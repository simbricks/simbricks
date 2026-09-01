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
from ..settings import simb_client
from ..utils import CREATED_BY_COLUMN, async_cli, print_table_generic

app = Typer(help="Managing SimBricks Systems.")

_SYSTEM_COLUMNS = ("id", CREATED_BY_COLUMN)


@app.command()
@async_cli()
async def ls(
    limit: Annotated[int, Option("--limit", "-n", help="Number of systems per page.")] = PAGE_SIZE,
    fetch_all: Annotated[
        bool,
        Option(
            "--all",
            "-a",
            help="Retrieve every system at once instead of paging through them.",
        ),
    ] = False,
):
    """List Systems.

    Pages interactively when there is more than one page and the output is a
    terminal. Left and right change page, g jumps back to the first page, r
    reloads the current one and q quits.
    """
    sbc = await simb_client()
    page_limit = None if fetch_all else limit
    await paged_ls(
        "Systems",
        _SYSTEM_COLUMNS,
        lambda cursor: opus_base.get_systems_page(sbc, cursor_next=cursor, limit=page_limit),
    )


@app.command()
@async_cli()
async def peek(
    limit: Annotated[int, Option("--limit", "-n", help="Number of systems to peek.")] = PEEK_COUNT,
):
    """Show the most recent Systems, 5 by default."""
    sbc = await simb_client()
    systems, _ = await opus_base.get_systems_page(sbc, limit=limit)
    print_table_generic("Latest Systems", systems, *_SYSTEM_COLUMNS)


@app.command()
@async_cli()
async def show(system_id: str):
    """Show individual System."""
    sbc = await simb_client()
    system = await sbc.get_system(system_id)
    print_table_generic("Systems", [system], *_SYSTEM_COLUMNS)


@app.command()
@async_cli()
async def rm(system_id: str):
    """Delete an individual run."""
    sbc = await simb_client()
    await sbc.delete_system(sys_id=system_id)
