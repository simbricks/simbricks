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
from ..settings import ns_client
from ..utils import async_cli, print_members_table, print_table_generic

app = Typer(help="Managing SimBricks namespaces.")

_NAMESPACE_COLUMNS = ("id", "name", "parent_id", "base_path")


@app.command()
@async_cli()
async def ls(
    limit: Annotated[
        int, Option("--limit", "-n", help="Number of namespaces per page.")
    ] = PAGE_SIZE,
    fetch_all: Annotated[
        bool,
        Option(
            "--all",
            "-a",
            help="Retrieve every namespace at once instead of paging through them.",
        ),
    ] = False,
):
    """List available namespaces.

    Pages interactively when there is more than one page and the output is a
    terminal. Left and right change page, g jumps back to the first page, r
    reloads the current one and q quits.
    """
    nsc = await ns_client()
    page_limit = None if fetch_all else limit
    await paged_ls(
        "Namespaces",
        _NAMESPACE_COLUMNS,
        lambda cursor: opus_base.get_namespaces_page(nsc, cursor_next=cursor, limit=page_limit),
    )


@app.command()
@async_cli()
async def peek(
    limit: Annotated[
        int, Option("--limit", "-n", help="Number of namespaces to peek.")
    ] = PEEK_COUNT,
):
    """Show the most recent namespaces, 5 by default."""
    nsc = await ns_client()
    namespaces, _ = await opus_base.get_namespaces_page(nsc, limit=limit)
    print_table_generic("Latest Namespaces", namespaces, *_NAMESPACE_COLUMNS)


@app.command()
@async_cli()
async def show(name: str):
    """List namespace with given name."""
    nsc = await ns_client()
    namespace = await nsc.get_ns_by_name(name)
    print_table_generic("Namespace", [namespace], *_NAMESPACE_COLUMNS)


@app.command()
@async_cli()
async def cur():
    """List current namespace."""
    nsc = await ns_client()
    namespace = await nsc.get_cur()
    print_table_generic("Namespace", [namespace], *_NAMESPACE_COLUMNS)


@app.command()
@async_cli()
async def create(name: str):
    """Create a new namespace."""
    nsc = await ns_client()
    namespace = await nsc.create_child_ns(name)
    print_table_generic("Namespace", [namespace], *_NAMESPACE_COLUMNS)


@app.command()
@async_cli()
async def rm(name: str):
    """Delete a namespace."""
    nsc = await ns_client()
    await nsc.delete_ns(name)
    print(f"Deleted namespace {name}.")


@app.command()
@async_cli()
async def members():
    """List all members."""
    nsc = await ns_client()
    members = await nsc.get_members()
    print_members_table(members)


@app.command()
@async_cli()
async def member_add(user: str, role: str):
    """Add member to namespace."""
    nsc = await ns_client()
    await nsc.add_member(role, user)
    print(f"Added user {user} with role {role}.")
