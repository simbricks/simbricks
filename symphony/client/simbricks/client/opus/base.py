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
import datetime
import itertools
import random
import typing

import rich
import rich.color
import rich.console
import rich.style
import rich.text

from simbricks.orchestration import instantiation, simulation, system
from simbricks.utils import artifatcs as utils_artifacts

from ..namespace import (
    NSClient,
    ResourceGroupClient,
    RunnerClient,
    SimBricksClient,
    simb_client,
)
from ..openapi.client.python.sim_bricks_api_client.models import (
    Instantiation as ApiInstantiation,
)
from ..openapi.client.python.sim_bricks_api_client.models import (
    Namespace,
    PaginationLinks,
    ResourceGroup,
    Run,
    Runner,
    RunOutput,
    RunOutputProxiesType0,
    RunOutputRuntimeType0,
    RunOutputSimulatorsType0,
    RunState,
)
from ..openapi.client.python.sim_bricks_api_client.models import (
    Simulation as ApiSimulation,
)
from ..openapi.client.python.sim_bricks_api_client.models import (
    System as ApiSystem,
)
from ..openapi.client.python.sim_bricks_api_client.types import Unset


async def still_running(run_id: str) -> bool:
    sbc = await simb_client()
    run = await sbc.get_run(run_id)
    return run is not None and (run.state == RunState.PENDING or run.state == RunState.RUNNING)


_RowT = typing.TypeVar("_RowT")


def _unwrap_page(
    data: list[_RowT] | None | Unset,
    links: PaginationLinks | None | Unset,
) -> tuple[list[_RowT], str | None]:
    """Unwrap a list response into its rows and the cursor for the page after it.

    The cursor is ``None`` when the server did not hand out a next one. Without
    a ``limit`` the server does not paginate and the whole list comes back in
    one response, so the cursor is ``None`` then too. This is the one place
    unwrapping the ``Unset | None | T`` unions of the generated client, so
    callers get plain values.
    """
    rows: list[_RowT] = data if isinstance(data, list) else []

    next_cursor: str | None = None
    if isinstance(links, PaginationLinks) and isinstance(links.next_, str):
        next_cursor = links.next_

    return rows, next_cursor


async def get_runs_page(
    sbc: SimBricksClient,
    cursor_next: str | None = None,
    limit: int | None = None,
) -> tuple[list[Run], str | None]:
    """Fetch a page of runs. See :func:`_unwrap_page` for the cursor semantics."""
    response = await sbc.get_runs(cursor_next=cursor_next, limit=limit)
    return _unwrap_page(response.data, response.links)


async def get_systems_page(
    sbc: SimBricksClient,
    cursor_next: str | None = None,
    limit: int | None = None,
) -> tuple[list[ApiSystem], str | None]:
    """Fetch a page of systems. See :func:`_unwrap_page` for the cursor semantics."""
    response = await sbc.get_systems(cursor_next=cursor_next, limit=limit)
    return _unwrap_page(response.data, response.links)


async def get_simulations_page(
    sbc: SimBricksClient,
    cursor_next: str | None = None,
    limit: int | None = None,
) -> tuple[list[ApiSimulation], str | None]:
    """Fetch a page of simulations. See :func:`_unwrap_page` for the cursor semantics."""
    response = await sbc.get_simulations(cursor_next=cursor_next, limit=limit)
    return _unwrap_page(response.data, response.links)


async def get_instantiations_page(
    sbc: SimBricksClient,
    cursor_next: str | None = None,
    limit: int | None = None,
) -> tuple[list[ApiInstantiation], str | None]:
    """Fetch a page of instantiations. See :func:`_unwrap_page` for the cursor semantics."""
    response = await sbc.get_instantiations(cursor_next=cursor_next, limit=limit)
    return _unwrap_page(response.data, response.links)


async def get_runners_page(
    rc: RunnerClient,
    cursor_next: str | None = None,
    limit: int | None = None,
) -> tuple[list[Runner], str | None]:
    """Fetch a page of runners. See :func:`_unwrap_page` for the cursor semantics."""
    response = await rc.list_runners(cursor_next=cursor_next, limit=limit)
    return _unwrap_page(response.data, response.links)


async def get_resource_groups_page(
    rgc: ResourceGroupClient,
    cursor_next: str | None = None,
    limit: int | None = None,
) -> tuple[list[ResourceGroup], str | None]:
    """Fetch a page of resource groups. See :func:`_unwrap_page` for the cursor semantics."""
    response = await rgc.get_all_rg(cursor_next=cursor_next, limit=limit)
    return _unwrap_page(response.data, response.links)


async def get_namespaces_page(
    nsc: NSClient,
    cursor_next: str | None = None,
    limit: int | None = None,
) -> tuple[list[Namespace], str | None]:
    """Fetch a page of child namespaces. See :func:`_unwrap_page` for the cursor semantics."""
    response = await nsc.get_all(cursor_next=cursor_next, limit=limit)
    return _unwrap_page(response.data, response.links)


class ConsoleLineGenerator:
    def __init__(self, run_id: str, follow: bool, sbc: SimBricksClient):
        self._sb_client: SimBricksClient = sbc
        self._run_id: str = run_id
        self._cursor_next: datetime.datetime | None = None
        self._proxies_seen_until_id: int | None = None
        self._follow = follow

    async def _fetch_next_output(self) -> list[tuple[str, str]]:
        output = await self._sb_client.get_run_console(
            run_id=self._run_id,
            cursor_next=self._cursor_next,
            cursor_prev=None,
            limit=None,
            wait=None,
        )

        if isinstance(output.links, PaginationLinks) and isinstance(output.links.next_, str):
            self._cursor_next = datetime.datetime.fromisoformat(output.links.next_)

        if not isinstance(output.data, RunOutput):
            print("No run output fetched")
            return []

        # the response groups lines per component, which loses the order they
        # were produced in, so collect timestamps and restore it below
        stamped: list[tuple[datetime.datetime, str, str]] = []

        if isinstance(output.data.simulators, RunOutputSimulatorsType0):
            for simulator in output.data.simulators.additional_properties.values():
                for output_lines in simulator.commands.additional_properties.values():
                    for output_line in output_lines:
                        stamped.append(
                            (output_line.produced_at, simulator.name, output_line.output)
                        )

        if isinstance(output.data.proxies, RunOutputProxiesType0):
            for proxy in output.data.proxies.additional_properties.values():
                for output_lines in proxy.commands.additional_properties.values():
                    for output_line in output_lines:
                        stamped.append((output_line.produced_at, proxy.name, output_line.output))

        if isinstance(output.data.runtime, RunOutputRuntimeType0):
            for output_lines in output.data.runtime.additional_properties.values():
                for output_line in output_lines:
                    stamped.append((output_line.produced_at, "runtime", output_line.output))

        stamped.sort(key=lambda entry: entry[0])
        return [(prefix, line) for _, prefix, line in stamped]

    async def generate_lines(self) -> typing.AsyncGenerator[tuple[str, str], None]:
        stop_after_next = not self._follow or not await still_running(self._run_id)
        while True:
            sleep_until = datetime.datetime.now() + datetime.timedelta(seconds=3)
            for prefix, line in await self._fetch_next_output():
                yield prefix, line
            if stop_after_next:
                break
            sleep_for = sleep_until - datetime.datetime.now()
            if sleep_for > datetime.timedelta(seconds=0):
                await asyncio.sleep(sleep_for.total_seconds())
            if not await still_running(self._run_id):
                # One more iteration to make sure we receive all output
                stop_after_next = True


class ComponentOutputPrettyPrinter:
    def __init__(self, console: rich.console.Console):
        self._console: rich.console.Console = console
        self._color_palette = [rich.color.Color.parse(f"color({i})") for i in range(1, 256, 4)]
        random.shuffle(self._color_palette)
        self._color_cycle = itertools.cycle(self._color_palette)
        self._prefix_colors = {}

    def print_line(self, prefix: str, line: str):
        if prefix not in self._prefix_colors:
            self._prefix_colors[prefix] = next(self._color_cycle)
        prefix_pretty = rich.text.Text(
            f"[{prefix}]", style=rich.style.Style(color=self._prefix_colors[prefix])
        )
        line_pretty = rich.text.Text(line)
        self._console.print(prefix_pretty, line_pretty)


async def follow_run(run_id: str) -> None:
    sbc = await simb_client()
    line_gen = ConsoleLineGenerator(run_id=run_id, follow=True, sbc=sbc)
    console = rich.console.Console()
    pretty_printer = ComponentOutputPrettyPrinter(console)

    with console.status(f"[bold green]Waiting for run {run_id} to finish..."):
        async for prefix, line in line_gen.generate_lines():
            pretty_printer.print_line(prefix, line)

        console.log(f"Run {run_id} finished")


async def submit_system(system: system.System) -> str:
    sbc = await simb_client()
    sys = await sbc.create_system(system)
    assert sys.id
    return sys.id


async def submit_simulation(system_id: str, simulation: simulation.Simulation) -> str:
    sbc = await simb_client()
    sim = await sbc.create_simulation(system_id, simulation)
    assert sim.id
    return sim.id


async def submit_instantiation(
    simulation_id: str, instantiation: instantiation.Instantiation
) -> str:
    simbricks_client = await simb_client()

    inst = await simbricks_client.create_instantiation(simulation_id, instantiation)
    assert isinstance(inst.id, str)

    if instantiation.input_artifact_paths:
        utils_artifacts.create_artifact(
            instantiation.input_artifact_name, instantiation.input_artifact_paths, flat=True
        )
        await simbricks_client.set_inst_input_artifact(inst.id, instantiation.input_artifact_name)

    fragment_id_map: dict[int, str] = {}
    assert isinstance(inst.fragments, list)
    for fragment in inst.fragments:
        assert isinstance(fragment.object_id, int)
        assert isinstance(fragment.id, str)
        fragment_id_map[fragment.object_id] = fragment.id
    for fragment in instantiation.fragments:
        if not fragment.input_artifact_paths:
            continue
        utils_artifacts.create_artifact(
            fragment.input_artifact_name, fragment.input_artifact_paths, flat=True
        )
        await simbricks_client.set_fragment_input_artifact(
            inst.id, fragment_id_map[fragment.id()], fragment.input_artifact_name
        )

    assert inst.id
    return inst.id


async def submit_run(instantiation_id: str) -> str:
    sbc = await simb_client()
    run = await sbc.create_run(instantiation_id)
    assert run.id
    return run.id


async def create_run(instantiation: instantiation.Instantiation) -> str:
    instantiation.finalize_validate()

    simulation = instantiation.simulation
    system = simulation.system

    system_id = await submit_system(system=system)
    sim_id = await submit_simulation(system_id=system_id, simulation=simulation)
    inst_id = await submit_instantiation(simulation_id=sim_id, instantiation=instantiation)

    run_id = await submit_run(instantiation_id=inst_id)
    return run_id
