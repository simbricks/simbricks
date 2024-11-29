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

import argparse
import asyncio

from simbricks.utils import load_mod as utils
from simbricks import client
import sys


async def main():
    parser = argparse.ArgumentParser(
        prog="sim-chef",
        description="CLI utility tool to send your SimBricks experiment script to the SimBricks backend for execution",
    )
    parser.add_argument(
        "--submit-run",
        metavar="SCRIPT.PY",
        help="submit SimBricks expiriment python script as a run",
    )
    parser.add_argument(
        "--check-run", metavar="RUNID", type=int, help="run id to check"
    )
    args = parser.parse_args()

    base_client = client.BaseClient(base_url="http://0.0.0.0:8000")
    namespace_client = client.NSClient(base_client=base_client, namespace="foo/bar/baz")
    system_client = client.SimBricksClient(ns_client=namespace_client)

    if args.submit_run:
        await submit_run(system_client, args.submit_run)
    elif args.check_run:
        await check_run(system_client, args.check_run)
    else:
        print("Error: Need to specify one of the actions")
        sys.exit(1)


async def submit_run(system_client: client.SimBricksClient, module_path):
    experiment_mod = utils.load_module(module_path=module_path)
    instantiations = experiment_mod.instantiations

    sb_inst = instantiations[0]
    sb_simulation = sb_inst.simulation
    sb_system = sb_simulation.system

    system = await system_client.create_system(sb_system)
    system_id = int(system["id"])
    system = await system_client.get_system(system_id)
    print(system)
    systems = await system_client.get_systems()
    print(systems)

    simulation = await system_client.create_simulation(system_id, sb_simulation)
    sim_id = int(simulation["id"])
    simulation = await system_client.get_simulation(sim_id)
    print(simulation)
    simulations = await system_client.get_simulations()
    print(simulations)

    instantiation = await system_client.create_instantiation(sim_id, None)
    inst_id = int(instantiation["id"])

    run = await system_client.create_run(inst_id)
    print(run)


async def check_run(system_client, run_id):
    run = await system_client.get_run(run_id)
    print(run)


if __name__ == "__main__":
    asyncio.run(main())
