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

import asyncio
import functools
from rich.table import Table
from rich.console import Console


def async_cli():
    """
    Decorator function turning async cli routines into regular ones for
    typer.
    """

    def decorator_async_cli(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return asyncio.run(f(*args, **kwargs))

        return wrapper

    return decorator_async_cli


def print_table_generic(title: str, to_print, *args):
    table = Table(title=title)

    for key in args:
        table.add_column(key)

    for val in to_print:
        row = []
        if hasattr(val, "__getitem__"):
            row = [str(val[key]) for key in args]
        else:
            row = [str(getattr(val, key)) for key in args]
        table.add_row(*row)

    console = Console()
    console.print(table)


def print_members_table(members: dict[str, list[dict]]):
    table = Table()
    table.add_column("Role")
    table.add_column("User")
    table.add_column("First")
    table.add_column("Last")
    for r, ms in members.items():
        for m in ms:
            table.add_row(r, m["username"], m["first_name"], m["last_name"])
    console = Console()
    console.print(table)
