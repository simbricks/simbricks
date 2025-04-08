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
import pydantic

import rich
import rich.color
import rich.style
import rich.text
import rich.console

from simbricks.orchestration import instantiation, simulation, system
from simbricks.schemas import base as schemas

from .. import client, provider


async def still_running(run_id: int) -> bool:
    run = await provider.client_provider.simbricks_client.get_run(run_id)
    return run.state == schemas.RunState.PENDING or run.state == schemas.RunState.RUNNING


class ConsoleLineGenerator:
    def __init__(self, run_id: int, follow: bool):
        self._sb_client: client.SimBricksClient = provider.client_provider.simbricks_client
        self._run_id: int = run_id
        self._simulators_seen_until_id: int | None = None
        self._proxies_seen_until_id: int | None = None
        self._follow = follow

    async def _fetch_next_output(self) -> list[str, str]:
        filter = schemas.ApiRunOutputFilter(
            simulator_seen_until_line_id=self._simulators_seen_until_id,
            proxy_seen_until_line_id=self._proxies_seen_until_id,
        )
        output = await self._sb_client.get_run_console(self._run_id, filter=filter)

        lines = []
        for simulator_id, simulator in output.simulators.items():
            for _, output_lines in simulator.commands.items():
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


async def follow_run(run_id: int) -> None:
    line_gen = ConsoleLineGenerator(run_id=run_id, follow=True)
    console = rich.console.Console()
    pretty_printer = ComponentOutputPrettyPrinter(console)

    with console.status(f"[bold green]Waiting for run {run_id} to finish...") as status:
        async for prefix, line in line_gen.generate_lines():
            pretty_printer.print_line(prefix, line)

        console.log(f"Run {run_id} finished")


async def submit_system(system: system.System) -> int:
    sys = await provider.client_provider.simbricks_client.create_system(system)
    assert sys.id
    return sys.id


async def submit_simulation(system_id: int, simulation: simulation.Simulation) -> int:
    sim = await provider.client_provider.simbricks_client.create_simulation(system_id, simulation)
    assert sim.id
    return sim.id


async def submit_instantiation(
    simulation_id: int, instantiation: instantiation.Instantiation
) -> int:
    inst = await provider.client_provider.simbricks_client.create_instantiation(
        simulation_id, instantiation
    )
    assert inst.id
    return inst.id


async def submit_run(instantiation_id: int) -> int:
    run = await provider.client_provider.simbricks_client.create_run(instantiation_id)
    assert run.id
    return run.id


async def create_run(instantiation: instantiation.Instantiation) -> int:
    simulation = instantiation.simulation
    system = simulation.system

    system_id = await submit_system(system=system)
    sim_id = await submit_simulation(system_id=system_id, simulation=simulation)
    inst_id = await submit_instantiation(simulation_id=sim_id, instantiation=instantiation)

    run_id = await submit_run(instantiation_id=inst_id)
    return run_id


T = typing.TypeVar("T")


async def create_event(rc: client.RunnerClient, event: schemas.ApiEventCreate_U) -> None:
    create_bundle = schemas.ApiEventBundle[schemas.ApiEventCreate_U]()
    create_bundle.add_event(event)

    await rc.create_events(create_bundle)


async def update_event(rc: client.RunnerClient, event: schemas.ApiEventUpdate_U) -> None:
    update_bundle = schemas.ApiEventBundle[schemas.ApiEventUpdate_U]()
    update_bundle.add_event(event)

    await rc.update_events(update_bundle)


async def fetch_events(
    rc: client.RunnerClient, query: schemas.ApiEventQuery_U, expected: T
) -> list[T]:
    query_bundle = schemas.ApiEventBundle[schemas.ApiEventQuery_U]()
    query_bundle.add_event(query)

    result_read_bundle = await rc.fetch_events(query_bundle)

    if result_read_bundle.empty():
        return []

    if "event_discriminator" not in expected.model_fields:
        raise Exception("unable to determine 'event dirciminator'")
    discr: str = expected.model_fields["event_discriminator"].default

    if discr not in result_read_bundle.events:
        raise Exception(
            f"could not fetch the required event type {discr} from {result_read_bundle}"
        )
    events = result_read_bundle.events[discr]

    adapter = pydantic.TypeAdapter(list[T])
    result_list = adapter.validate_python(events)
    return result_list
