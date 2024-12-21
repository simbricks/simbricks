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
from ..state import state
from ..utils import async_cli, print_runner_table


app = Typer(help="Managing SimBricks runners.")


@app.command()
@async_cli()
async def ls():
    """List runners."""
    runs = await state.runner_client.list_runners()
    print_runner_table(runs)


@app.command()
@async_cli()
async def show(runner_id: int):
    """Show individual runner."""
    runner = await state.runner_client.get_runner(runner_id=runner_id)
    print_runner_table([runner])


@app.command()
@async_cli()
async def delete(runner_id: int):
    """Delete an individual runner."""
    await state.runner_client.delete_runner(runner_id=runner_id)


@app.command()
@async_cli()
async def create(label: str, tags: list[str]):
    """Update a runner with the the given label and tags."""
    runner = await state.runner_client.create_runner(label=label, tags=tags)
    print_runner_table([runner])
