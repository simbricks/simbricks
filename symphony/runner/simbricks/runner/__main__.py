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
import json
import pathlib
import rich
from rich.console import Console
from simbricks.runtime import simulation_executor
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.runtime import command_executor
from simbricks import client

verbose = True

# TODO: FIXME, create a custom listener for the runner to register + create backend endpoint to update the output etc.
async def periodically_update(rc: client.RunnerClient, run_id: int, 
                              listeners: list[command_executor.LegacyOutputListener]) -> None:
    try:
        while True:
            all_out: list[str] = []
            for listener in listeners:
                all_out.extend(listener.merged_output)
                listener.merged_output = []
            
            if len(all_out) > 0:
                print(all_out)
                await rc.update_run(run_id, "running", json.dumps(all_out))
            
            await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        pass

async def run_instantiation(rc: client.RunnerClient, run_id: int, inst: inst_base.Instantiation) -> dict:
    executor = command_executor.LocalExecutor()
    runner = simulation_executor.SimulationSimpleRunner(executor, inst, verbose)
    await runner.prepare()
    listeners = []
    for sim in inst.simulation.all_simulators():
        listener = command_executor.LegacyOutputListener()
        runner.add_listener(sim, listener)
        listeners.append(listener)

    update_task = asyncio.create_task(periodically_update(rc=rc, run_id=run_id, listeners=listeners))
    output = await runner.run()
    update_task.cancel()

    return output.toJSON()


async def amain():
    base_client = client.BaseClient(base_url="http://127.0.0.1:8000")
    namespace_client = client.NSClient(base_client=base_client, namespace="foo/bar/baz")
    sb_client = client.SimBricksClient(namespace_client)
    rc = client.RunnerClient(namespace_client, 42)

    workdir = pathlib.Path("./runner-work").resolve()

    console = Console()
    with console.status(f"[bold green]Waiting for valid run...") as status:
        while True:
            run_obj = await rc.next_run()
            if not run_obj:
                console.log("No valid run, sleeping")
                await asyncio.sleep(5)
                continue

            run_id = run_obj["id"]
            console.log(f"Preparing run {run_id}")
            run_workdir = workdir / f"run-{run_id}"
            run_workdir.mkdir(parents=True)

            inst_obj = await sb_client.get_instantiation(run_obj["instantiation_id"])
            sim_obj = await sb_client.get_simulation(inst_obj["simulation_id"])
            sys_obj = await sb_client.get_system(sim_obj["system_id"])

            system = sys_base.System.fromJSON(json.loads(sys_obj["sb_json"]))
            simulation = sim_base.Simulation.fromJSON(system, json.loads(sim_obj["sb_json"]))

            # TODO: set from args
            env = inst_base.InstantiationEnvironment(workdir=run_workdir)

            inst = inst_base.Instantiation(sim=simulation)
            inst.env = env
            inst.preserve_tmp_folder = False
            inst.create_checkpoint = True

            console.log(f"Starting run {run_id}")
            await rc.update_run(run_id, "running", "")
            out = await run_instantiation(rc, run_id, inst)
            if inst.create_artifact:
                await sb_client.set_run_artifact(run_id, inst.artifact_name)
            await rc.update_run(run_id, "completed", json.dumps(out))
            console.log(f"Finished run {run_id}")


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
