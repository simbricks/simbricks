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
import sys
import typing
from pathlib import Path

import rich
import rich.console
from typer import Argument, BadParameter, Option, Typer
from typing_extensions import Annotated

import simbricks.utils.load_mod as load_mod
from simbricks.client.opus import base as opus_base
from simbricks.client.streams import forward as stream_forward
from simbricks.client.streams.session import RunStreams

from ..pager import PAGE_SIZE, PEEK_COUNT, paged_ls
from ..settings import simb_client
from ..utils import CREATED_BY_COLUMN, async_cli, print_table_generic

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base


app = Typer(help="Managing SimBricks runs.")

_RUN_COLUMNS = ("id", "instantiation_id", "state", CREATED_BY_COLUMN)


@app.command()
@async_cli()
async def ls(
    limit: Annotated[int, Option("--limit", "-n", help="Number of runs per page.")] = PAGE_SIZE,
    fetch_all: Annotated[
        bool,
        Option(
            "--all",
            "-a",
            help="Retrieve every run at once instead of paging through them.",
        ),
    ] = False,
):
    """List runs.

    Pages interactively when there is more than one page and the output is a
    terminal. Left and right change page, g jumps back to the first page, r
    reloads the current one and q quits.
    """
    sbc = await simb_client()
    page_limit = None if fetch_all else limit
    await paged_ls(
        "Runs",
        _RUN_COLUMNS,
        lambda cursor: opus_base.get_runs_page(sbc, cursor_next=cursor, limit=page_limit),
    )


@app.command()
@async_cli()
async def peek(
    limit: Annotated[int, Option("--limit", "-n", help="Number of runs to peek.")] = PEEK_COUNT,
):
    """Show the most recent runs, 5 by default."""
    sbc = await simb_client()
    runs, _ = await opus_base.get_runs_page(sbc, limit=limit)
    print_table_generic("Latest Runs", runs, *_RUN_COLUMNS)


@app.command()
@async_cli()
async def show(run_id: str):
    """Show individual run."""
    sbc = await simb_client()
    run = await sbc.get_run(run_id)
    print_table_generic("Run", [run], *_RUN_COLUMNS)


@app.command()
@async_cli()
async def kill(run_id: str):
    """Kill individual run."""
    sbc = await simb_client()
    await sbc.kill_run(run_id)


@app.command()
@async_cli()
async def sigusr1(run_id: str):
    """Send sigusr1 to run."""
    sbc = await simb_client()
    await sbc.sigusr1_run(run_id)


@app.command()
@async_cli()
async def follow(run_id: str):
    """Follow individual run as it executes."""
    await opus_base.follow_run(run_id=run_id)


@app.command()
@async_cli()
async def rc(run_id: str):
    """Print a runs console completely."""
    sbc = await simb_client()
    console = rich.console.Console()
    pretty_printer = opus_base.ComponentOutputPrettyPrinter(console)
    with console.status(f"[bold green]Waiting for console output of run {run_id} ..."):
        async for prefix, line in opus_base.ConsoleLineGenerator(
            run_id=run_id, follow=False, sbc=sbc
        ).generate_lines():
            pretty_printer.print_line(prefix, line)


@app.command()
@async_cli()
async def ls_rf(run_id: Annotated[str, Argument(help="The run id.")]):
    """List all run fragments of a run."""
    sbc = await simb_client()
    run_fragments = await sbc.get_all_run_fragments(run_id)
    print_table_generic(
        "Run Fragments",
        run_fragments.data,
        "id",
        "run_id",
        "runner_id",
        "state",
        "output_artifact_exists",
    )


@app.command()
@async_cli()
async def goa(
    run_id: Annotated[str, Argument(help="The run id.")],
    run_fragment_id: Annotated[str, Argument(help="The run fragment id.")],
    path: Annotated[
        Path, Argument(help="The path where to store the output artifact.", writable=True)
    ] = Path("./"),
):
    """Retrieve the output artifact that is stored for a run fragment."""
    if path.is_dir():
        path = path / Path(f"output_artifact_{run_fragment_id}.zip")
    if not path.parent.exists():
        raise RuntimeError(f"The path '{path.parent}' does not exist.")

    sbc = await simb_client()
    await sbc.get_run_fragment_output_artifact(run_id, run_fragment_id, path.as_posix())


@app.command()
@async_cli()
async def rm(run_id: str):
    """Delete an individual run."""
    sbc = await simb_client()
    await sbc.delete_run(run_id)


@app.command()
@async_cli()
async def submit(
    path: Annotated[Path, Argument(help="Python simulation script to submit.")],
    follow: Annotated[
        bool,
        Option(
            "--follow",
            "-f",
            help="Wait for run to terminate and show output live. This only works in case a single instantiation is defined in your experiment scripts instantiations list.",
        ),
    ] = False,
):
    """Submit a SimBricks python simulation script to run."""

    experiment_mod = load_mod.load_module(module_path=path.as_posix())
    instantiations: list[inst_base.Instantiation] = experiment_mod.instantiations

    sbc = await simb_client()
    run_id = None
    for sb_inst in instantiations:
        run_id = await opus_base.create_run(instantiation=sb_inst)
        run = await sbc.get_run(run_id)
        assert run and run_id == run.id
        print_table_generic("Run", [run], *_RUN_COLUMNS)

    if follow and len(instantiations) > 1:
        print("Won't follow execution as more than one run was submitted.")
    elif follow and run_id:
        await opus_base.follow_run(run_id=run_id)


@app.command()
@async_cli()
async def create(
    inst_id: str,
    follow: Annotated[
        bool,
        Option(
            "--follow",
            "-f",
            help="Wait for run to terminate and show output live.",
        ),
    ] = False,
):
    """Create a virtual prototype run based on an already submitted configuration."""
    sbc = await simb_client()
    run = await sbc.create_run(inst_id)
    print_table_generic("Run", [run], *_RUN_COLUMNS)

    if follow and isinstance(run.id, str):
        await opus_base.follow_run(run_id=run.id)


async def _fragment_id(streams: RunStreams, frag: str | None) -> str:
    if frag is not None:
        return frag
    ids = await streams.fragment_ids()
    if len(ids) != 1:
        raise BadParameter(f"run has {len(ids)} fragments, pick one with --frag: {ids}")
    return ids[0]


def _parse_forward(spec: str) -> tuple[str, int, str]:
    """``[bind:]port:target``, e.g. ``7000:tcp:connect:127.0.0.1:7000``."""
    parts = spec.split(":", 2)
    if len(parts) == 3 and parts[0].isdigit():
        bind, port, target = "127.0.0.1", int(parts[0]), f"{parts[1]}:{parts[2]}"
        # the target still holds mode and the rest: "tcp:connect:127.0.0.1:7000"
        return bind, port, target
    parts = spec.split(":", 3)
    if len(parts) == 4 and parts[1].isdigit():
        return parts[0], int(parts[1]), f"{parts[2]}:{parts[3]}"
    raise BadParameter(f"expected [bind:]port:target, got {spec!r}")


@app.command()
@async_cli()
async def forward(
    run_id: str,
    local: Annotated[
        list[str],
        Option(
            "-L",
            help="Forward a local port into the executor: [bind:]port:<target>, e.g. "
            "7000:tcp:connect:127.0.0.1:7000 for a gem5 gdb stub.",
        ),
    ] = [],
    remote: Annotated[
        list[str],
        Option(
            "-R",
            help="Serve a listener inside the executor from a local port: "
            "[host:]port:<listen target>, e.g. 5555:tcp:listen:127.0.0.1:5555.",
        ),
    ] = [],
    frag: Annotated[
        str | None, Option("--frag", help="Run fragment to reach (needed if there are several).")
    ] = None,
):
    """Forward ports between this machine and a running simulation's executor."""
    if not local and not remote:
        raise BadParameter("nothing to forward, give -L and/or -R")
    sbc = await simb_client()
    streams = RunStreams(sbc, run_id)
    fragment_id = await _fragment_id(streams, frag)
    console = rich.console.Console()

    servers = []
    watchers = []
    try:
        for spec in local:
            bind, port, target = _parse_forward(spec)
            servers.append(
                await stream_forward.forward_tcp(streams, fragment_id, bind, port, target)
            )
            console.print(f"[green]-L[/green] {bind}:{port} -> {target}")
        for spec in remote:
            bind, port, target = _parse_forward(spec)
            await stream_forward.reverse_tcp(streams, fragment_id, target, bind, port)
            accept, on_stream = stream_forward.serve_reverse_connections(target, bind, port)
            watchers.append(asyncio.create_task(streams.watch(on_stream, accept)))
            console.print(f"[green]-R[/green] {target} -> {bind}:{port}")
        console.print("forwarding, press Ctrl+C to stop")
        await asyncio.Event().wait()
    finally:
        for watcher in watchers:
            watcher.cancel()
        for server in servers:
            server.close()
        await streams.close()


@app.command()
@async_cli()
async def tail(
    run_id: str,
    path: Annotated[str, Argument(help="File path relative to the run's work directory.")],
    follow: Annotated[
        bool, Option("--follow", "-f", help="Keep reading as the file grows.")
    ] = False,
    frag: Annotated[
        str | None, Option("--frag", help="Run fragment to reach (needed if there are several).")
    ] = None,
):
    """Print a file from a running simulation's work directory, e.g. a simulator's debug log."""
    sbc = await simb_client()
    streams = RunStreams(sbc, run_id)
    fragment_id = await _fragment_id(streams, frag)

    async def to_stdout(data: bytes) -> None:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    try:
        await stream_forward.read_file(streams, fragment_id, path, to_stdout, follow=follow)
    finally:
        await streams.close()
