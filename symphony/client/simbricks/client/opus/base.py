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
import rich.style
import rich.text
import rich.console

from simbricks.orchestration import instantiation, simulation, system
from simbricks.utils import artifatcs as utils_artifacts

from ..namespace import simb_client, SimBricksClient
from ..openapi.client.sim_bricks_api_client.models import (
    RunState,
    PaginationLinks,
    RunOutput,
    RunOutputSimulatorsType0,
)


async def still_running(run_id: str) -> bool:
    run = await simb_client().get_run(run_id)
    return run.state == RunState.PENDING or run.state == RunState.RUNNING


class ConsoleLineGenerator:
    def __init__(self, run_id: str, follow: bool):
        self._sb_client: SimBricksClient = simb_client()
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

        if isinstance(output.links, PaginationLinks):
            self._cursor_next = datetime.datetime.fromisoformat(output.links.next_)

        lines = []
        if not isinstance(output.data, RunOutput):
            return lines

        # TODO: handle proxy output as well
        assert output.data.simulators and isinstance(
            output.data.simulators, RunOutputSimulatorsType0
        )
        simulators: RunOutputSimulatorsType0 = output.data.simulators

        for simulator_id, simulator in simulators.additional_properties.items():
            for _, output_lines in simulator.commands.additional_properties.items():
                for output_line in output_lines:
                    assert output_line.id is not None
                    lines.append((simulator.name, output_line.output))
                    if self._simulators_seen_until_id is None:
                        self._simulators_seen_until_id = output_line.id
                    else:
                        self._simulators_seen_until_id = max(
                            self._simulators_seen_until_id, output_line.id
                        )

        return lines

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
    line_gen = ConsoleLineGenerator(run_id=run_id, follow=True)
    console = rich.console.Console()
    pretty_printer = ComponentOutputPrettyPrinter(console)

    with console.status(f"[bold green]Waiting for run {run_id} to finish...") as status:
        async for prefix, line in line_gen.generate_lines():
            pretty_printer.print_line(prefix, line)

        console.log(f"Run {run_id} finished")


async def submit_system(system: system.System) -> str:
    sys = await simb_client().create_system(system)
    assert sys.id
    return sys.id


async def submit_simulation(system_id: str, simulation: simulation.Simulation) -> str:
    sim = await simb_client().create_simulation(system_id, simulation)
    assert sim.id
    return sim.id


async def submit_instantiation(
    simulation_id: str, instantiation: instantiation.Instantiation
) -> str:
    simbricks_client = simb_client()

    inst = await simbricks_client.create_instantiation(simulation_id, instantiation)

    if instantiation.input_artifact_paths:
        utils_artifacts.create_artifact(
            instantiation.input_artifact_name, instantiation.input_artifact_paths
        )
        await simbricks_client.set_inst_input_artifact(inst.id, instantiation.input_artifact_name)

    fragment_id_map: dict[int, int] = {}
    for fragment in inst.fragments:
        fragment_id_map[fragment.object_id] = fragment.id
    for fragment in instantiation.fragments:
        if not fragment.input_artifact_paths:
            continue
        utils_artifacts.create_artifact(fragment.input_artifact_name, fragment.input_artifact_paths)
        await simbricks_client.set_fragment_input_artifact(
            inst.id, fragment_id_map[fragment.id()], fragment.input_artifact_name
        )

    assert inst.id
    return inst.id


async def submit_run(instantiation_id: str) -> str:
    run = await simb_client().create_run(instantiation_id)
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
