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

from pathlib import Path
from typer import Typer, Option
from typing_extensions import Annotated
from rich.table import Table
from rich.console import Console
from ..state import state
from ..utils import async_cli

app = Typer(help="Managing SimBricks namespaces.")


def print_namespace_table(namespaces) -> None:
    table = Table()
    table.add_column("Id")
    table.add_column("name")
    table.add_column("parent")
    for ns in namespaces:
        table.add_row(str(ns["id"]), str(ns["name"]), str(ns["parent_id"]))

    console = Console()
    console.print(table)


@app.command()
@async_cli()
async def ls():
    """List available namespaces."""
    client = state.ns_client()

    namespaces = await client.get_all()
    print_namespace_table(namespaces)


@app.command()
@async_cli()
async def ls_id(ident: int):
    """List namespace with given id ident."""
    client = state.ns_client()

    namespace = await client.get_ns(ident)
    print_namespace_table([namespace])


@app.command()
@async_cli()
async def ls_cur():
    """List current namespace."""
    client = state.ns_client()

    namespace = await client.get_cur()
    print_namespace_table([namespace])


@app.command()
@async_cli()
async def create(name: str):
    """Create a new namespace."""

    client = state.ns_client()

    # create namespace relative to current namespace
    cur_ns = await client.get_cur()
    cur_ns_id = int(cur_ns["id"])

    # create the actual namespace
    namespace = await client.create(parent_id=cur_ns_id, name=name)
    ns_id = namespace["id"]

    print(f"Creating namespace {name} in {state.namespace}. New namespace: {ns_id}")
