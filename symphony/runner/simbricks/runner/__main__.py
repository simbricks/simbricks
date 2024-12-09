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
from simbricks.runtime import simulation_executor
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.runtime import command_executor
from simbricks import client

verbose = True

async def run_instantiation(inst: inst_base.Instantiation) -> dict:
    executor = command_executor.LocalExecutor()
    runner = simulation_executor.SimulationSimpleRunner(
                executor, inst, verbose
            )
    await runner.prepare()
    output = await runner.run()
    return output.__dict__


async def amain():
    base_client = client.BaseClient()
    namespace_client = client.NSClient(base_client=base_client, namespace="foo/bar/baz")
    sb_client = client.SimBricksClient(namespace_client)
    rc = client.RunnerClient(namespace_client, 42)

    workdir = pathlib.Path('./runner-work').resolve()

    while True:
        run_obj = await rc.next_run()
        if not run_obj:
            print('No valid run, sleeping')
            await asyncio.sleep(5)
            continue
        
        run_id = run_obj["id"]
        print(f'Preparing run {run_id}')
        run_workdir = workdir / f'run-{run_id}'
        run_workdir.mkdir(parents=True)

        inst_obj = await sb_client.get_instantiation(run_obj['instantiation_id'])
        sim_obj = await sb_client.get_simulation(inst_obj['simulation_id'])
        sys_obj = await sb_client.get_system(sim_obj['system_id'])

        system = sys_base.System.fromJSON(json.loads(sys_obj['sb_json']))
        simulation = sim_base.Simulation.fromJSON(system, json.loads(sim_obj['sb_json']))

         # TODO: set from args
        env = inst_base.InstantiationEnvironment(workdir = run_workdir)

        inst = inst_base.Instantiation(sim=simulation)
        inst.env = env
        inst.preserve_tmp_folder = False
        inst.create_checkpoint = True

        print(f'Starting run {run_id}')

        await rc.update_run(run_id, 'running', '')
        out = await run_instantiation(inst)
        if inst.create_artifact:
            await sb_client.set_run_artifact(run_id, inst.artifact_name)

        print(f'Finished run {run_id}')

        await rc.update_run(run_id, 'completed', json.dumps(out))

def main():
    asyncio.run(amain())

if __name__ == "__main__":
    main()
