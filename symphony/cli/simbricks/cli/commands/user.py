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
from simbricks.client import auth
from simbricks.client.user import user_client
from ..utils import async_cli, print_table_generic

app = Typer(help="Managing SimBricks User.")


@app.command()
@async_cli()
async def authenticate():
    """Explicitly trigger user authentication. (Usually not necessary to do this explicitly)"""
    await auth.TokenProvider().access_token()


@app.command()
@async_cli()
async def info():
    """Retrieve information about my user."""
    uc = await user_client()
    user = await uc.user_info()
    print_table_generic("User", [user],  "id", "username", "email", "first_name", "last_name")


@app.command()
@async_cli()
async def def_ns_mem():
    """Retrieve the current users default namespace membership."""
    uc = await user_client()
    membership = await uc.default_namespace_membership()
    print_table_generic("Default Namesapce Membership", [membership],  "username", "email", "first_name", "last_name", "role", "namespace_full_path")


@app.command()
@async_cli()
async def set_def_ns_mem(ns_path: str):
    """Set the current users default namespace membership."""
    uc = await user_client()
    membership = await uc.set_default_ns_membership(ns_path)
    print_table_generic("Default Namesapce Membership", [membership],  "username", "email", "first_name", "last_name", "role", "namespace_full_path")



@app.command()
@async_cli()
async def memberships():
    """List a users namespace memberships."""
    uc = await user_client()
    memberships = await uc.memberships()
    print_table_generic("Namesapce Memberships", memberships.data,  "username", "email", "first_name", "last_name", "role", "namespace_full_path")
