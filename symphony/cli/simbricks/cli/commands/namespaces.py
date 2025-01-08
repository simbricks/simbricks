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

from typer import Typer
from simbricks.client.provider import client_provider
from ..utils import async_cli, print_table_generic, print_members_table

app = Typer(help="Managing SimBricks namespaces.")


@app.command()
@async_cli()
async def ls():
    """List available namespaces."""
    client = client_provider.ns_client

    namespaces = await client.get_all()
    print_table_generic("Namespaces", namespaces, "id", "name", "parent_id")


@app.command()
@async_cli()
async def ls_id(ident: int):
    """List namespace with given id ident."""
    client = client_provider.ns_client

    namespace = await client.get_ns(ident)
    print_table_generic("Namespace", [namespace], "id", "name", "parent_id")


@app.command()
@async_cli()
async def ls_cur():
    """List current namespace."""
    client = client_provider.ns_client

    namespace = await client.get_cur()
    print_table_generic("Namespace", [namespace], "id", "name", "parent_id")


@app.command()
@async_cli()
async def create(name: str):
    """Create a new namespace."""

    client = client_provider.ns_client

    # create namespace relative to current namespace
    cur_ns = await client.get_cur()
    cur_ns_id = int(cur_ns["id"])

    # create the actual namespace
    namespace = await client.create(parent_id=cur_ns_id, name=name)
    print_table_generic("Namespace", [namespace], "id", "name", "parent_id")


@app.command()
@async_cli()
async def delete(ident: int):
    """Delete a namespace."""

    client = client_provider.ns_client
    await client.delete_ns(ident)
    print(f"Deleted namespace with id {ident}.")


@app.command()
@async_cli()
async def members():
    """List all members."""

    client = client_provider.ns_client
    members = await client.get_members()
    print_members_table(members)


@app.command()
@async_cli()
async def member_add(user: str, role: str):
    """Add member to namespace."""

    client = client_provider.ns_client
    members = await client.add_member(role, user)
    print(f"Added user {user} with role {role}.")