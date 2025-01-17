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
from simbricks.cli.commands import (
    audit,
    admin,
    namespaces,
    rg,
    runs,
    systems,
    simulations,
    instantiations,
    runners,
)
from simbricks.client.provider import client_provider
from simbricks.cli.utils import async_cli

app = Typer()
app.add_typer(namespaces.app, name="ns")
app.add_typer(runs.app, name="runs")
app.add_typer(audit.app, name="audit")
app.add_typer(admin.app, name="admin")
app.add_typer(systems.app, name="systems")
app.add_typer(simulations.app, name="sims")
app.add_typer(instantiations.app, name="insts")
app.add_typer(runners.app, name="runners")
app.add_typer(rg.app, name="rg")


@app.callback()
@async_cli()
async def amain(
    ns: Annotated[str, Option(help="Namespace to operate in.")] = "foo/bar/baz",
    runner_ident: Annotated[int, Option(help="Runner ident to operate on.")] = -1,
):
    client_provider.namespace = ns
    client_provider.runner_id = runner_ident


def main():
    app()


if __name__ == "__main__":
    main()
