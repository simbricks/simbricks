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

from ..state import state
from ..utils import async_cli, print_namespace_table

app = Typer(help="SimBricks admin commands.")


@app.command()
@async_cli()
async def ns_ls():
    """List all available namespaces."""
    client = state.admin_client
    namespaces = await client.get_all_ns()
    print_namespace_table(namespaces)


@app.command()
@async_cli()
async def ns_ls_id(ident: int):
    """List namespace with given id ident."""
    client = state.admin_client
    namespace = await client.get_ns(ns_id=ident)
    print_namespace_table([namespace])


@app.command()
@async_cli()
async def ns_create(name: str, parent_id: Annotated[int, Option(help="optional parent namesapce")] = None):
    """Create a new namespace."""
    client = state.admin_client
    namespace = await client.create_ns(parent_id=parent_id, name=name)
    ns_id = namespace["id"]
    print(f"Creating namespace {name} in {state.namespace}. New namespace: {ns_id}")


@app.command()
@async_cli()
async def ns_delete(ident: int):
    """Delete a namespace."""
    client = state.admin_client
    await client.delete(ns_id=ident)
    print(f"Deleted namespace with id {ident}.")
