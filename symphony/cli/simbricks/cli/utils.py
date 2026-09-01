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
import typing

from rich.console import Console
from rich.table import Table
from typer import Exit

from simbricks.client.namespace import NsMember, NsRole


def async_cli():
    """
    Decorator function turning async cli routines into regular ones for
    typer.
    """

    def decorator_async_cli(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return asyncio.run(f(*args, **kwargs))
            except KeyboardInterrupt:
                # Ctrl+C surfaces out of asyncio.run, so the commands
                # themselves cannot catch it. Interrupting an interactive or
                # long-running command is normal, exit like a shell instead of
                # dumping a traceback on the user.
                raise Exit(code=130) from None

        return wrapper

    return decorator_async_cli


Column = str | tuple[str, typing.Callable[[typing.Any], str]]
"""A table column: an attribute name, or a (header, cell renderer) pair."""


def _attribute_cell(key: str, val) -> str:
    if hasattr(val, key):
        return str(getattr(val, key))
    # elif hasattr(val, "__getitem__"):
    #     return str(val[key])
    raise Exception(f"could not find attribute {key}")


def _resolve_column(column: Column) -> tuple[str, typing.Callable[[typing.Any], str]]:
    if isinstance(column, str):
        return column, functools.partial(_attribute_cell, column)
    return column


def build_table(title: str | None, to_print, *args: Column) -> Table:
    table = Table(title=title)

    columns = [_resolve_column(column) for column in args]

    for header, _ in columns:
        table.add_column(header)

    for val in to_print:
        if val is None:
            continue

        table.add_row(*(cell(val) for _, cell in columns))

    return table


def print_table_generic(title: str, to_print, *args: Column):
    console = Console()
    console.print(build_table(title, to_print, *args))


def print_members_table(members: dict[NsRole, list[NsMember]]):
    table = Table()
    table.add_column("Role")
    table.add_column("User")
    table.add_column("First")
    table.add_column("Last")
    for r, ms in members.items():
        for m in ms:
            table.add_row(m.role, m.username, m.first_name, m.last_name)
    console = Console()
    console.print(table)
