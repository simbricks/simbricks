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

import sys
import asyncio
import json
import pathlib
from rich.console import Console
from simbricks.runtime import simulation_executor
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.runtime import command_executor
from simbricks import client
from .settings import runner_settings as runset
from simbricks.utils import artifatcs as art


class ConsoleLineListener(command_executor.OutputListener):

    # TODO: make actually use of this
    def __init__(self, rc: client.RunnerClient, run_id: int, prefix: str = ""):
        super().__init__()
        self._prefix: str = prefix
        self._rc: client.RunnerClient = rc
        self._run_id: int = run_id

    async def handel_out(self, lines: list[str]) -> None:
        if len(lines) < 1:
            return
        await self._rc.send_out(self._run_id, self._prefix, False, lines)

    async def handel_err(self, lines: list[str]) -> None:
        if len(lines) < 1:
            return
        await self._rc.send_out(self._run_id, self._prefix, True, lines)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj.update({"prefix": self._prefix})
        return json_obj


class Runner:

    class Run:
        def __init__(self, ident: int, inst: inst_base.Instantiation):
            self.id: int = ident
            self.inst: inst_base.Instantiation = inst
            self.exec_task: asyncio.Task | None = None
            self.cancelled: bool = False

    def __init__(self, base_url: str, workdir: str, namespace: str, ident: int):
        self._base_url: str = base_url
        self._workdir: pathlib.Path = pathlib.Path(workdir).resolve()
        self._namespace: str = namespace
        self._ident: int = ident
        self._base_client = client.BaseClient(base_url=base_url)
        self._namespace_client = client.NSClient(base_client=self._base_client, namespace=namespace)
        self._sb_client = client.SimBricksClient(self._namespace_client)
        self._rc = client.RunnerClient(self._namespace_client, ident)

        self._console = Console()
        self._to_run_queue: asyncio.Queue = asyncio.Queue()  # queue of run ids to run next
        self._cur_run: Runner.Run | None = None  # currently executed run

    async def _fetch_and_assemble_run(self, to_fetch_run_id: int) -> Run:
        run_obj_list = await self._rc.filter_get_runs(run_id=to_fetch_run_id, state="pending")
        if not run_obj_list or len(run_obj_list) != 1:
            raise Exception(f"could not fetch run with id {to_fetch_run_id} that is still 'pending'")
        run_obj = run_obj_list[0]

        run_id = to_fetch_run_id
        self._console.log(f"Preparing run {run_id}")

        run_workdir = self._workdir / f"run-{run_id}"
        run_workdir.mkdir(parents=True)

        inst_obj = await self._sb_client.get_instantiation(run_obj["instantiation_id"])
        sim_obj = await self._sb_client.get_simulation(inst_obj["simulation_id"])
        sys_obj = await self._sb_client.get_system(sim_obj["system_id"])

        system = sys_base.System.fromJSON(json.loads(sys_obj["sb_json"]))
        simulation = sim_base.Simulation.fromJSON(system, json.loads(sim_obj["sb_json"]))
        env = inst_base.InstantiationEnvironment(workdir=run_workdir)  # TODO
        inst = inst_base.Instantiation(sim=simulation)
        inst.env = env
        inst.preserve_tmp_folder = False
        inst.create_checkpoint = True
        # inst.artifact_paths = [f"{run_workdir}/output"] # create an artifact
        inst.artifact_paths = []  # create NO artifact

        run = Runner.Run(ident=run_id, inst=inst)
        return run

    async def _handel_events(self) -> None:
        try:
            while True:
                # fetch all events not handeled yet
                events = list(await self._rc.get_events(run_id=None, action=None, limit=None, event_status="pending"))
                if self._cur_run:
                    run_events = list(
                        await self._rc.get_events(
                            run_id=self._cur_run.id,
                            action=None,
                            limit=None,
                            event_status="pending",
                        )
                    )
                    events.extend(run_events)
                # handel the fetched events
                for event in events:
                    event_id = event["id"]
                    self._console.log(f"try to handel event {event}")

                    event_status = "completed"
                    match event["action"]:
                        case "kill":
                            if not self._cur_run or not self._cur_run.exec_task:
                                event_status = "cancelled"
                            else:
                                self._cur_run.cancelled = True
                                self._cur_run.exec_task.cancel()
                        case "heartbeat":
                            await self._rc.send_heartbeat()
                        case "start_run":
                            to_fetch_id = event["run_id"] if event["run_id"] else None
                            if not to_fetch_id:
                                event_status = "cancelled"
                            else:
                                await self._to_run_queue.put(to_fetch_id)
                        case "simulation_status":
                            event_status = "cancelled"
                            run_id = event["run_id"] if event["run_id"] else None
                            if not self._cur_run or not self._cur_run.exec_task or not run_id:
                                event_status = "cancelled"
                            else:
                                # TODO: implement
                                self._console.log("handling of the simulation_status event is not implemented yet")

                    await self._rc.update_runner_event(
                        event_id=event_id, event_status=event_status, action=None, run_id=None
                    )
                    self._console.log(f"handeled event {event}")

                await asyncio.sleep(3)

        except asyncio.CancelledError:
            pass

    async def _execute_run(self) -> None:
        try:
            while True:
                to_fetch_id = await self._to_run_queue.get()
                self._cur_run = await self._fetch_and_assemble_run(to_fetch_run_id=to_fetch_id)

                assert self._cur_run
                try:
                    self._console.log(f"Starting run {self._cur_run.id}")

                    await self._rc.update_run(self._cur_run.id, "running", "")

                    executor = command_executor.LocalExecutor()
                    runner = simulation_executor.SimulationSimpleRunner(executor, self._cur_run.inst, runset().verbose)
                    await runner.prepare()

                    listeners = []
                    for sim in self._cur_run.inst.simulation.all_simulators():
                        listener = ConsoleLineListener(rc=self._rc, run_id=self._cur_run.id)
                        runner.add_listener(sim, listener)
                        listeners.append((sim.name, listener))

                    simulation_task = asyncio.create_task(runner.run())
                    self._cur_run.exec_task = simulation_task
                    res = await simulation_task

                    output_path = self._cur_run.inst.get_simulation_output_path()
                    res.dump(outpath=output_path)

                    if self._cur_run.inst.create_artifact:
                        art.create_artifact(
                            artifact_name=self._cur_run.inst.artifact_name,
                            paths_to_include=self._cur_run.inst.artifact_paths,
                        )
                        await self._sb_client.set_run_artifact(self._cur_run.id, self._cur_run.inst.artifact_name)

                    status = "error" if res.failed() else "completed"
                    await self._rc.update_run(self._cur_run.id, status, output="")
                    self._console.log(f"Finished run {self._cur_run.id}")
                except Exception as err:
                    if self._cur_run:
                        status = "cancelled" if self._cur_run.cancelled else "error"
                        await self._rc.update_run(self._cur_run.id, state=status, output="")
                        self._console.log(f"stopped execution of run {self._cur_run.id} {status}")
                    else:
                        raise err
                self._cur_run = None

        except asyncio.CancelledError:
            if self._cur_run:
                await self._rc.update_run(self._cur_run.id, "cancelled", output="")
            return
        except Exception as error:
            self._console.log(f"encountered fatal error: {error}")
            sys.exit(1)

    async def run(self) -> None:
        with self._console.status(f"[bold green]Waiting for valid run...") as status:
            execute_runs_task = asyncio.create_task(self._execute_run())
            handel_events_task = asyncio.create_task(self._handel_events())
            try:
                _, pending = await asyncio.wait(
                    [execute_runs_task, handel_events_task], return_when=asyncio.FIRST_COMPLETED
                )
                map(lambda t: t.cancel(), pending)
            except asyncio.CancelledError:
                execute_runs_task.cancel()
                handel_events_task.cancel()


async def amain():
    runner = Runner(
        base_url=runset().base_url,
        workdir=pathlib.Path("./runner-work").resolve(),
        namespace=runset().namespace,
        ident=runset().runner_id,
    )

    await runner.run()


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
