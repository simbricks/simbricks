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
import logging
import pathlib
import sys

from simbricks import client
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.system import base as sys_base
from simbricks.runtime import simulation_executor
from simbricks.utils import artifatcs as art

from .settings import runner_settings as runset


class Run:
    def __init__(
        self,
        run_id: int,
        inst: inst_base.Instantiation,
        runner: simulation_executor.SimulationExecutor,
    ):
        self.run_id: int = run_id
        self.inst: inst_base.Instantiation = inst
        self.cancelled: bool = False
        self.runner: simulation_executor.SimulationExecutor = runner
        self.exec_task: asyncio.Task | None = None


class Runner:

    def __init__(self, base_url: str, workdir: str, namespace: str, ident: int):
        self._base_url: str = base_url
        self._workdir: pathlib.Path = pathlib.Path(workdir).resolve()
        self._namespace: str = namespace
        self._ident: int = ident
        self._base_client = client.BaseClient(base_url=base_url)
        self._namespace_client = client.NSClient(base_client=self._base_client, namespace=namespace)
        self._sb_client = client.SimBricksClient(self._namespace_client)
        self._rc = client.RunnerClient(self._namespace_client, ident)

        # self._cur_run: Run | None = None  # currently executed run
        # self._to_run_queue: asyncio.Queue = asyncio.Queue()  # queue of run ids to run next
        self._run_map: dict[int, Run] = {}

    async def _fetch_assemble_inst(self, run_id: int) -> inst_base.Instantiation:
        LOGGER.debug(f"fetch and assemble instantiation related to run {run_id}")

        run_obj_list = await self._rc.filter_get_runs(run_id=run_id, state="pending")
        if not run_obj_list or len(run_obj_list) != 1:
            msg = f"could not fetch run with id {run_id} that is still 'pending'"
            LOGGER.error(msg)
            raise Exception(msg)
        run_obj = run_obj_list[0]

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
        return inst

    async def _prepare_run(self, run_id: int) -> Run:
        LOGGER.debug(f"prepare run {run_id}")

        inst = await self._fetch_assemble_inst(run_id=run_id)

        callbacks = simulation_executor.SimulationExecutorCallbacks(inst)
        runner = simulation_executor.SimulationExecutor(inst, callbacks, runset().verbose)
        await runner.prepare()

        run = Run(run_id=run_id, inst=inst, runner=runner)
        return run

    async def _start_run(self, run: Run) -> None:
        sim_task: asyncio.Task | None = None
        try:
            LOGGER.info(f"start run {run.run_id}")

            await self._rc.update_run(run.run_id, "running", "")
            sim_task = asyncio.create_task(run.runner.run())
            res = await sim_task

            output_path = run.inst.get_simulation_output_path()
            res.dump(outpath=output_path)
            if run.inst.create_artifact:
                art.create_artifact(
                    artifact_name=run.inst.artifact_name,
                    paths_to_include=run.inst.artifact_paths,
                )
                await self._sb_client.set_run_artifact(run.run_id, run.inst.artifact_name)

            status = "error" if res.failed() else "completed"
            await self._rc.update_run(run.run_id, status, output="")

            await run.runner.cleanup()

            LOGGER.info(f"finished run {run.run_id}")

        except asyncio.CancelledError:
            LOGGER.debug("_start_sim handel cancelled error")
            if sim_task:
                sim_task.cancel()
            await self._rc.update_run(run.run_id, state="cancelled", output="")
            LOGGER.info(f"cancelled execution of run {run.run_id}")
            raise

        except Exception as ex:
            LOGGER.debug("_start_sim handel fatal error")
            if sim_task:
                sim_task.cancel()
            await self._rc.update_run(run_id=run.run_id, state="error", output="")
            LOGGER.error(f"error while executing run {run.run_id}: {ex}")
            raise ex

    async def _cancel_all_tasks(self) -> None:
        for _, run in self._run_map.items():
            if run.exec_task.done():
                continue

            run.exec_task.cancel()
            await run.exec_task

    async def _handel_events(self) -> None:
        try:
            while True:
                # fetch all events not handeled yet
                events = list(
                    await self._rc.get_events(
                        run_id=None, action=None, limit=None, event_status="pending"
                    )
                )
                for run_id in list(self._run_map.keys()):
                    run = self._run_map[run_id]
                    # check if run finished and cleanup map
                    if run.exec_task.done():
                        run = self._run_map.pop(run_id)
                        await run.exec_task
                        LOGGER.debug(f"removed run {run_id} from run_map")
                        assert run_id not in self._run_map
                        continue
                    # only fecth events in case run is not finished yet
                    run_events = list(
                        await self._rc.get_events(
                            run_id=run_id,
                            action=None,
                            limit=None,
                            event_status="pending",
                        )
                    )
                    events.extend(run_events)

                LOGGER.debug(f"events fetched ({len(events)}): {events}")

                # handel the fetched events
                for event in events:
                    event_id = event["id"]
                    run_id = event["run_id"] if event["run_id"] else None
                    LOGGER.debug(f"try to handel event {event}")

                    event_status = "completed"
                    match event["action"]:
                        case "kill":
                            if run_id and not run_id in self._run_map:
                                event_status = "cancelled"
                            else:
                                run = self._run_map[run_id]
                                run.exec_task.cancel()
                                await run.exec_task
                                LOGGER.debug(f"executed kill to cancel execution of run {run_id}")
                        case "heartbeat":
                            await self._rc.send_heartbeat()
                            LOGGER.debug(f"send heartbeat")
                        case "start_run":
                            if not run_id or run_id in self._run_map:
                                LOGGER.debug(
                                    f"cannot start run, no run id or run with given id is being executed"
                                )
                                event_status = "cancelled"
                            else:
                                run = await self._prepare_run(run_id=run_id)
                                run.exec_task = asyncio.create_task(self._start_run(run=run))
                                self._run_map[run_id] = run
                                LOGGER.debug(f"started execution of run {run_id}")
                        case "simulation_status":
                            if not run_id or not run_id in self._run_map:
                                event_status = "cancelled"
                            else:
                                run = self._run_map[run_id]
                                await run.runner.sigusr1()
                                LOGGER.debug(f"send sigusr1 to run {run_id}")

                    await self._rc.update_runner_event(
                        event_id=event_id, event_status=event_status, action=None, run_id=None
                    )
                    LOGGER.info(f"handeled event {event_id}")

                await asyncio.sleep(3)

        except asyncio.CancelledError:
            await self._cancel_all_tasks()

        except Exception as exc:
            await self._cancel_all_tasks()
            LOGGER.error(f"an error occured while running: {exc}")
            raise exc

    async def run(self) -> None:
        LOGGER.info("STARTED RUNNER")
        LOGGER.debug(
            f" runner params: base_url={self._base_url}, workdir={self._workdir}, namespace={self._namespace}, _ident={self._ident}"
        )

        # execute_runs_task = asyncio.create_task(self._execute_run())
        # handel_events_task = asyncio.create_task(self._handel_events())
        try:
            await self._handel_events()
            # _, pending = await asyncio.wait(
            #     [execute_runs_task, handel_events_task], return_when=asyncio.FIRST_COMPLETED
            # )
            # map(lambda t: t.cancel(), pending)
        except Exception as exc:
            LOGGER.error(f"fatal error {exc}")
            sys.exit(1)
            # execute_runs_task.cancel()
            # handel_events_task.cancel()

        LOGGER.info("TERMINATED RUNNER")


async def amain():
    runner = Runner(
        base_url=runset().base_url,
        workdir=pathlib.Path("./runner-work").resolve(),
        namespace=runset().namespace,
        ident=runset().runner_id,
    )

    await runner.run()


def setup_logger() -> logging.Logger:
    level = runset().log_level
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger(__name__)
    return logger


LOGGER = setup_logger()


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
