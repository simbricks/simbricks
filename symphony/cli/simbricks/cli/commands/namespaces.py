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
from simbricks.client import ns_client
from ..utils import async_cli, print_table_generic, print_members_table

app = Typer(help="Managing SimBricks namespaces.")


@app.command()
@async_cli()
async def ls():
    """List available namespaces."""
    nsc = await ns_client()
    namespaces = await nsc.get_all()
    print_table_generic("Namespaces", namespaces.data, "id", "name", "parent_id", "base_path")


@app.command()
@async_cli()
async def show(name: str):
    """List namespace with given name."""
    nsc = await ns_client()
    namespace = await nsc.get_ns_by_name(name)
    print_table_generic("Namespace", [namespace], "id", "name", "parent_id", "base_path")


@app.command()
@async_cli()
async def cur():
    """List current namespace."""
    nsc = await ns_client()
    namespace = await nsc.get_cur()
    print_table_generic("Namespace", [namespace], "id", "name", "parent_id", "base_path")


@app.command()
@async_cli()
async def create(name: str):
    """Create a new namespace."""
    nsc = await ns_client()
    namespace = await nsc.create_child_ns(name)
    print_table_generic("Namespace", [namespace], "id", "name", "parent_id", "base_path")


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
    members = await nsc.add_member(role, user)
    print(f"Added user {user} with role {role}.")
