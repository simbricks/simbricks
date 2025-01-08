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

import typing
import asyncio
import rich
from .. import client, provider
from simbricks.orchestration import system
from simbricks.orchestration import simulation
from simbricks.orchestration import instantiation


async def still_running(run_id: int) -> bool:
    run = await provider.client_provider.simbricks_client.get_run(run_id)
    return run["state"] == "pending" or run["state"] == "running"


class ConsoleLineGenerator:
    def __init__(self, run_id: int):
        self._sb_client: client.SimBricksClient = provider.client_provider.simbricks_client
        self._run_id: int = run_id
        self._line_buffer: list[dict] = []
        self._read_index: int = 0
        self._prev_len: int = 0
        self._index = 0

    def _data_left(self) -> bool:
        return self._read_index < len(self._line_buffer)

    async def _fetch_output(self) -> None:
        while await still_running(run_id=self._run_id):
            output = await self._sb_client.get_run_console(self._run_id)
            if len(output) != self._prev_len:
                extend = output[self._prev_len :]
                self._line_buffer = extend
                self._prev_len = len(output)
                self._read_index = 0
                break

            await asyncio.sleep(3)

    async def _has_more(self) -> bool:
        if not self._data_left():
            await self._fetch_output()
        return self._data_left()

    async def generate_lines(self) -> typing.AsyncGenerator[dict, None]:
        while await self._has_more():
            line = self._line_buffer[self._read_index]
            self._read_index += 1
            yield line


async def follow_run(run_id: int) -> None:
    line_gen = ConsoleLineGenerator(run_id=run_id)
    console = rich.console.Console()

    with console.status(f"[bold green]Waiting for run {run_id} to finish...") as status:
        async for line in line_gen.generate_lines():
            console.log(line["simulator"] + ":" + line["output"])

        console.log(f"Run {run_id} finished")


async def submit_system(system: system.System) -> int:
    system = await provider.client_provider.simbricks_client.create_system(system)
    system_id = int(system["id"])
    return system_id


async def submit_simulation(system_id: int, simulation: simulation.Simulation) -> int:
    simulation = await provider.client_provider.simbricks_client.create_simulation(system_id, simulation)
    sim_id = int(simulation["id"])
    return sim_id


async def submit_instantiation(simulation_id: int, instantiation: instantiation.Instantiation) -> int:
    # TODO: the instantiation itself is currently not used as this is not yet supported
    instantiation = await provider.client_provider.simbricks_client.create_instantiation(simulation_id, None)
    inst_id = int(instantiation["id"])
    return inst_id


async def submit_run(instantiation_id: int) -> int:
    run = await provider.client_provider.simbricks_client.create_run(instantiation_id)
    run_id = int(run["id"])
    return run_id


async def create_run(instantiation: instantiation.Instantiation) -> int:
    simulation = instantiation.simulation
    system = simulation.system

    system_id = await submit_system(system=system)
    sim_id = await submit_simulation(system_id=system_id, simulation=simulation)
    inst_id = await submit_instantiation(simulation_id=sim_id, instantiation=instantiation)

    run_id = await submit_run(instantiation_id=inst_id)
    return run_id
