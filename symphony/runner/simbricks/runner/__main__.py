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
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import pathlib
import traceback
import typing
import uuid

from simbricks import client
from simbricks.client.opus import base as opus_base
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.system import base as sys_base
from simbricks.runner import settings
from simbricks.runtime import simulation_executor as sim_exec
from simbricks.schemas import base as schemas
from simbricks.utils import base as utils_base
from simbricks.utils import artifatcs as utils_art

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import proxy as inst_proxy


class RunnerSimulationExecutorCallbacks(sim_exec.SimulationExecutorCallbacks):

    def __init__(
        self,
        instantiation: inst_base.Instantiation,
        rc: client.RunnerClient,
        run_id: int,
    ):
        super().__init__(instantiation)
        self._instantiation = instantiation
        self._client: client.RunnerClient = rc
        self._run_id: int = run_id

    # ---------------------------------------
    # Callbacks related to whole simulation -
    # ---------------------------------------

    async def simulation_prepare_cmd_start(self, cmd: str) -> None:
        LOGGER.debug(f"+ [prepare] {cmd}")
        # TODO Send executed prepare command to backend

    async def simulation_prepare_cmd_stdout(self, cmd: str, lines: list[str]) -> None:
        super().simulation_prepare_cmd_stdout(cmd, lines)
        for line in lines:
            LOGGER.debug(f"[prepare] {line}")
        # TODO Send simulation prepare output to backend

    async def simulation_prepare_cmd_stderr(self, cmd: str, lines: list[str]) -> None:
        super().simulation_prepare_cmd_stderr(cmd, lines)
        for line in lines:
            LOGGER.debug(f"[prepare] {line}")
        # TODO Send simulation prepare output to backend

    # -----------------------------
    # Simulator-related callbacks -
    # -----------------------------

    async def _send_state_simulator_event(
        self,
        simulator_id: int,
        sim_name: str | None = None,
        cmd: str | None = None,
        state: schemas.RunComponentState | None = None,
    ) -> None:
        event = schemas.ApiSimulatorStateChangeEventCreate(
            runner_id=self._client.runner_id,
            run_id=self._run_id,
            simulator_id=simulator_id,
            simulator_state=state,
            simulator_name=sim_name,
            command=cmd,
        )
        await opus_base.create_event(self._client, event)

    async def _send_out_simulator_events(
        self, simulator_id: int, lines: list[str], stderr: bool
    ) -> None:
        event_bundle = schemas.ApiEventBundle[schemas.ApiSimulatorOutputEventCreate]()
        for line in lines:
            event = schemas.ApiSimulatorOutputEventCreate(
                runner_id=self._client.runner_id,
                run_id=self._run_id,
                simulator_id=simulator_id,
                output=line,
                is_stderr=stderr,
            )
            event_bundle.add_event(event)

        await self._client.create_events(event_bundle)

    async def simulator_prepare_started(self, sim: sim_base.Simulator, cmd: str) -> None:
        LOGGER.debug(f"+ [{sim.full_name()}] {cmd}")
        await self._send_state_simulator_event(
            sim.id(), sim.full_name(), cmd, schemas.RunComponentState.PREPARING
        )

    async def simulator_prepare_exited(self, sim: sim_base.Simulator, exit_code: int) -> None:
        LOGGER.debug(f"- [{sim.full_name()}] exited with code {exit_code}")
        # Report exit code to backend. Right now, we just do this as a line of console output.
        await self._send_out_simulator_events(
            sim.id(), [f"prepare command exited with code {exit_code}"], False
        )

    async def simulator_prepare_stdout(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        for line in lines:
            LOGGER.debug(f"[{sim.full_name()}] {line}")
        await self._send_out_simulator_events(sim.id(), lines, False)

    async def simulator_prepare_stderr(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        for line in lines:
            LOGGER.debug(f"[{sim.full_name()}] {line}")
        await self._send_out_simulator_events(sim.id(), lines, True)

    async def simulator_started(self, sim: sim_base.Simulator, cmd: str) -> None:
        LOGGER.debug(f"+ [{sim.full_name()}] {cmd}")
        await self._send_state_simulator_event(
            sim.id(), sim.full_name(), cmd, schemas.RunComponentState.STARTING
        )

    async def simulator_ready(self, sim: sim_base.Simulator) -> None:
        # TODO: Due to coroutine scheduling, simulator might have already been terminated and
        # simulator_exited was already called
        await self._send_state_simulator_event(sim.id(), state=schemas.RunComponentState.RUNNING)

    async def simulator_exited(self, sim: sim_base.Simulator, exit_code: int) -> None:
        LOGGER.debug(f"- [{sim.full_name()}] exited with code {exit_code}")
        # Report exit code to backend. Right now, we just do this as a line of console output.
        await self._send_out_simulator_events(sim.id(), [f"exited with code {exit_code}"], False)
        await self._send_state_simulator_event(sim.id(), state=schemas.RunComponentState.TERMINATED)

    async def simulator_stdout(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        for line in lines:
            LOGGER.debug(f"[{sim.full_name()}] {line}")
        await self._send_out_simulator_events(sim.id(), lines, False)

    async def simulator_stderr(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        for line in lines:
            LOGGER.debug(f"[{sim.full_name()}] {line}")
        await self._send_out_simulator_events(sim.id(), lines, True)

    # -------------------------
    # Proxy-related callbacks -
    # -------------------------

    async def _send_state_proxy_event(
        self,
        proxy_id: int,
        proxy_name: str | None = None,
        state: schemas.RunComponentState | None = None,
        proxy_ip: str | None = None,
        proxy_port: int | None = None,
    ) -> None:
        event = schemas.ApiProxyStateChangeEventCreate(
            runner_id=self._client.runner_id,
            run_id=self._run_id,
            proxy_name=proxy_name,
            proxy_id=proxy_id,
            proxy_state=state,
            proxy_ip=proxy_ip,
            proxy_port=proxy_port,
        )
        await opus_base.create_event(self._client, event)

    async def _send_out_proxy_events(self, proxy_id: int, lines: list[str], stderr: bool) -> None:
        event_bundle = schemas.ApiEventBundle[schemas.ApiProxyOutputEventCreate]()
        for line in lines:
            event = schemas.ApiProxyOutputEventCreate(
                runner_id=self._client.runner_id,
                run_id=self._run_id,
                proxy_id=proxy_id,
                output=line,
                is_stderr=stderr,
            )
            event_bundle.add_event(event)

        await self._client.create_events(event_bundle)

    async def proxy_started(self, proxy: inst_proxy.Proxy, cmd: str) -> None:
        LOGGER.debug(f"+ [{proxy.name}] {cmd}")

        await self._send_state_proxy_event(proxy.id(), state=schemas.RunComponentState.STARTING)

    async def proxy_ready(self, proxy: inst_proxy.Proxy) -> None:
        LOGGER.debug(f"[{proxy.name}] has started successfully")
        await self._send_state_proxy_event(
            proxy.id(),
            state=schemas.RunComponentState.RUNNING,
            proxy_ip=proxy._ip,
            proxy_port=proxy._port,
        )

    async def proxy_exited(self, proxy: inst_proxy.Proxy, exit_code: int) -> None:
        LOGGER.debug(f"- [{proxy.name}] exited with code {exit_code}")
        await self._send_out_proxy_events(proxy.id(), [f"exited with code {exit_code}", False])
        await self._send_state_proxy_event(proxy.id(), state=schemas.RunComponentState.TERMINATED)

    async def proxy_stdout(self, proxy: inst_proxy.Proxy, lines: list[str]) -> None:
        for line in lines:
            LOGGER.debug(f"[{proxy.name}] {line}")
        await self._send_out_proxy_events(proxy.id(), lines, False)

    async def proxy_stderr(self, proxy: inst_proxy.Proxy, lines: list[str]) -> None:
        for line in lines:
            LOGGER.debug(f"[{proxy.name}] {line}")
        await self._send_out_proxy_events(proxy.id(), lines, True)


class Run:
    def __init__(
        self,
        run_id: int,
        inst: inst_base.Instantiation,
        callbacks: RunnerSimulationExecutorCallbacks,
        runner: sim_exec.SimulationExecutor,
    ) -> None:
        self.run_id: int = run_id
        self.inst: inst_base.Instantiation = inst
        self.callbacks: RunnerSimulationExecutorCallbacks = callbacks
        self.cancelled: bool = False
        self.runner: sim_exec.SimulationExecutor = runner
        self.exec_task: asyncio.Task | None = None


class Runner:

    def __init__(
        self, base_url: str, workdir: str, namespace: str, ident: int, polling_delay_sec: int
    ):
        self._base_url: str = base_url
        self._workdir: pathlib.Path = pathlib.Path(workdir).resolve()
        self._polling_delay_sec: int = polling_delay_sec
        self._namespace: str = namespace
        self._ident: int = ident
        self._base_client = client.BaseClient(base_url=base_url)
        self._namespace_client = client.NSClient(base_client=self._base_client, namespace=namespace)
        self._sb_client = client.SimBricksClient(self._namespace_client)
        self._rc = client.RunnerClient(self._namespace_client, ident)

        # self._cur_run: Run | None = None  # currently executed run
        # self._to_run_queue: asyncio.Queue = asyncio.Queue()  # queue of run ids to run next
        self._run_map: dict[int, Run] = {}

    async def _fetch_assemble_inst(
        self, run_id: int, start_event: schemas.ApiRunEventStartRunRead
    ) -> inst_base.Instantiation:
        LOGGER.debug(f"fetch and assemble instantiation related to run {run_id}")

        # For now we expect to always have exactly one fragment per runner
        if len(start_event.fragments) != 1:
            raise RuntimeError("There must be exactly one fragment assigned to a runner")

        run_obj_list = await self._rc.filter_get_runs(run_id=run_id, state="pending")
        if not run_obj_list or len(run_obj_list) != 1:
            msg = f"could not fetch run with id {run_id} that is still 'pending'"
            LOGGER.error(msg)
            raise Exception(msg)
        run_obj = run_obj_list[0]

        run_workdir = self._workdir / f"run-{run_id}"
        if run_workdir.exists():
            LOGGER.warning(
                f"the directory {run_workdir} already exists, will create a new one using a uuid"
            )
            run_workdir = self._workdir / f"run-{run_id}-{str(uuid.uuid4())}"
        run_workdir.mkdir(parents=True)

        # Either use the JSON blobs included in the event or fetch the JSON from the backend
        if (
            start_event.inst is not None
            and start_event.system is not None
            and start_event.simulation is not None
        ):
            inst_sb_json = start_event.inst
            sim_sb_json = start_event.simulation
            sys_sb_json = start_event.system
        else:
            assert run_obj.instantiation_id
            inst_obj = await self._sb_client.get_instantiation(run_obj.instantiation_id)
            assert inst_obj.simulation_id
            inst_sb_json = inst_obj.sb_json
            sim_obj = await self._sb_client.get_simulation(inst_obj.simulation_id)
            assert sim_obj.system_id
            sim_sb_json = sim_obj.sb_json
            sys_obj = await self._sb_client.get_system(sim_obj.system_id)
            sys_sb_json = sys_obj.sb_json

        system = sys_base.System.fromJSON(json.loads(sys_sb_json))
        simulation = sim_base.Simulation.fromJSON(system, json.loads(sim_sb_json))
        inst = inst_base.Instantiation.fromJSON(simulation, json.loads(inst_sb_json))

        env = inst_base.InstantiationEnvironment(
            workdir=run_workdir,
            simbricksdir=pathlib.Path(
                "/simbricks"
            ),  # TODO: we should not set the simbricks dir here
        )  # TODO
        inst.env = env
        inst.assigned_fragment = inst.get_fragment(start_event.fragments[0])
        return inst

    async def _prepare_run(self, run_id: int, start_event: schemas.ApiRunEventStartRunRead) -> Run:
        LOGGER.debug(f"prepare run {run_id}")

        inst = await self._fetch_assemble_inst(run_id, start_event)
        callbacks = RunnerSimulationExecutorCallbacks(inst, self._rc, run_id)
        runner = sim_exec.SimulationExecutor(inst, callbacks, settings.RunnerSettings().verbose)
        await runner.prepare()

        run = Run(run_id=run_id, inst=inst, runner=runner, callbacks=callbacks)
        return run

    async def _start_run(self, run: Run) -> None:
        sim_task: asyncio.Task | None = None
        try:
            LOGGER.info(f"start run {run.run_id}")

            await self._rc.update_run(run.run_id, schemas.RunState.RUNNING, "")

            # TODO: allow for proper checkpointing run
            sim_task = asyncio.create_task(run.runner.run())
            res = await sim_task

            output_path = run.inst.env.get_simulation_output_path()
            res.dump(outpath=output_path)  # TODO: FIXME
            if run.inst.create_artifact:
                utils_art.create_artifact(
                    artifact_name=run.inst.artifact_name,
                    paths_to_include=run.inst.artifact_paths,
                )
                await self._sb_client.set_run_artifact(run.run_id, run.inst.artifact_name)

            status = schemas.RunState.ERROR if res.failed() else schemas.RunState.COMPLETED
            await self._rc.update_run(run.run_id, status, output="")

            await run.runner.cleanup()

            LOGGER.info(f"finished run {run.run_id}")

        except asyncio.CancelledError:
            LOGGER.debug("_start_sim handle cancelled error")
            if sim_task:
                sim_task.cancel()
            await self._rc.update_run(run.run_id, state=schemas.RunState.CANCELLED, output="")
            LOGGER.info(f"cancelled execution of run {run.run_id}")

        except Exception as ex:
            LOGGER.debug("_start_sim handle error")
            if sim_task:
                sim_task.cancel()
            await self._rc.update_run(run_id=run.run_id, state=schemas.RunState.ERROR, output="")
            LOGGER.error(f"error while executing run {run.run_id}: {ex}")

    async def _cancel_all_tasks(self) -> None:
        for _, run in self._run_map.items():
            if run.exec_task.done():
                continue

            run.exec_task.cancel()
            await run.exec_task

    async def _handle_general_run_events(
        self,
        events: list[schemas.ApiRunEventRead],
        updates: schemas.ApiEventBundle[schemas.ApiEventUpdate_U],
    ) -> None:
        events = schemas.validate_list_type(events, schemas.ApiRunEventRead)
        for event in events:
            update = schemas.ApiRunEventUpdate(
                id=event.id, runner_id=self._ident, run_id=event.run_id
            )
            run_id = event.run_id
            match event.run_event_type:
                case schemas.RunEventType.KILL:
                    if run_id and not run_id in self._run_map:
                        update.event_status = schemas.ApiEventStatus.CANCELLED
                    else:
                        run = self._run_map[run_id]
                        run.exec_task.cancel()
                        await run.exec_task
                        update.event_status = schemas.ApiEventStatus.COMPLETED
                        LOGGER.debug(f"executed kill to cancel execution of run {run_id}")
                    break
                case schemas.RunEventType.SIMULATION_STATUS:
                    if not run_id or not run_id in self._run_map:
                        update.event_status = schemas.ApiEventStatus.CANCELLED
                    else:
                        run = self._run_map[run_id]
                        await run.runner.sigusr1()
                        update.event_status = schemas.ApiEventStatus.COMPLETED
                        LOGGER.debug(f"send sigusr1 to run {run_id}")
                    break
                case schemas.RunEventType.START_RUN:
                    assert (
                        event.event_discriminator
                        == schemas.ApiRunEventStartRunRead.event_discriminator
                    )
                    event = schemas.ApiRunEventStartRunRead.model_validate(event)
                    if run_id in self._run_map:
                        LOGGER.debug(
                            f"cannot start run, run with id {run_id} is already being executed"
                        )
                        update.event_status = schemas.ApiEventStatus.CANCELLED
                    else:
                        try:
                            # The await here is deliberate, we want to make sure that we block here
                            # and do not poll for / process further events before the run is fully
                            # set up.

                            # For example, we need this property when dealing with distributed
                            # simulations. Other runners might send events to us, so we need the
                            # necessary data structures to handle them to be fully set up.
                            run = await self._prepare_run(run_id, event)

                            run.exec_task = asyncio.create_task(self._start_run(run=run))
                            self._run_map[run_id] = run
                            update.event_status = schemas.ApiEventStatus.COMPLETED
                            LOGGER.debug(f"started execution of run {run_id}")
                        except Exception:
                            trace = traceback.format_exc()
                            LOGGER.error(f"could not prepare run {run_id}: {trace}")
                            await self._rc.update_run(run_id, schemas.RunState.ERROR, "")
                            update.event_status = schemas.ApiEventStatus.ERROR

            updates.add_event(update)
            LOGGER.info(f"handled run related event {event.id}")

    async def _handle_proxy_ready_run_events(
        self, events: list[schemas.ApiProxyStateChangeEventRead]
    ) -> None:
        for event in events:
            # TODO: FIXME proxy related events are currently not stored in the db, hence there is no
            # point in updating an event itself. NOTE however that events are send to the backend in
            # order to trigger a state change on the proxy db object. Similarly one can query for
            # events that return the state of a proxy.

            run_id = event.run_id
            if run_id and not run_id in self._run_map:
                continue

            run = self._run_map[run_id]
            await run.runner.mark_external_proxies_running(event.proxy_id)
            LOGGER.debug(
                f"processed ApiProxyReadyRunEventRead for proxy {event.proxy_id} and marked it ready"
            )

    async def _handle_runner_events(
        self,
        events: list[schemas.ApiRunnerEventRead],
        updates: schemas.ApiEventBundle[schemas.ApiEventUpdate_U],
    ) -> schemas.ApiEventBundle[schemas.ApiEventUpdate_U]:
        events = schemas.ApiRunnerEventRead_List_A.validate_python(events)
        for event in events:
            update = schemas.ApiRunnerEventUpdate(id=event.id, runner_id=self._ident)
            match event.runner_event_type:
                case schemas.RunnerEventType.heartbeat:
                    await self._rc.send_heartbeat()
                    update.event_status = schemas.ApiEventStatus.COMPLETED
                    LOGGER.debug(f"send heartbeat")

            updates.add_event(update)
            LOGGER.info(f"handled runner related event {event.id}")

    async def _handle_events(self) -> None:
        try:
            await self._rc.runner_started()

            while True:
                # fetch all events not handled yet
                event_query_bundle = schemas.ApiEventBundle[schemas.ApiEventQuery_U]()

                # query events for the runner itsel that do not relate to a specific run
                runner_event_q = schemas.ApiRunnerEventQuery(
                    runner_ids=[self._ident], event_status=[schemas.ApiEventStatus.PENDING]
                )
                event_query_bundle.add_event(runner_event_q)

                # query run related events that do not trigger the start of a run. We explicitly
                # exclude start_run events as we need the json blobs to start them. Therefore we
                # create an extra query for them.
                non_start_type = utils_base.enum_subs(
                    schemas.RunEventType, schemas.RunEventType.START_RUN
                )
                run_event_q = schemas.ApiRunEventQuery(
                    runner_ids=[self._ident],
                    event_status=[schemas.ApiEventStatus.PENDING],
                    run_event_type=non_start_type,
                )
                event_query_bundle.add_event(run_event_q)

                # query events that start a run
                start_run_event_q = schemas.ApiRunEventStartRunQuery(
                    runner_ids=[self._ident], event_status=[schemas.ApiEventStatus.PENDING]
                )
                event_query_bundle.add_event(start_run_event_q)

                # query events indicating that proxies are now ready
                state_change_q = schemas.ApiProxyStateChangeEventQuery(
                    run_ids=list(self._run_map.keys()),
                    proy_states=[schemas.RunComponentState.RUNNING],
                )
                event_query_bundle.add_event(state_change_q)

                for run_id in list(self._run_map.keys()):
                    run = self._run_map[run_id]
                    # check if run finished and cleanup map
                    if run.exec_task and run.exec_task.done():
                        run = self._run_map.pop(run_id)
                        LOGGER.debug(f"removed run {run_id} from run_map")
                        assert run_id not in self._run_map
                        continue

                fetched_events_bundle = await self._rc.fetch_events(event_query_bundle)

                LOGGER.debug(
                    f"events fetched ({len(fetched_events_bundle.events)}): {fetched_events_bundle.events}"
                )

                update_events_bundle = schemas.ApiEventBundle[schemas.ApiEventUpdate_U]()
                for key in fetched_events_bundle.events.keys():
                    events = fetched_events_bundle.events[key]
                    match key:
                        # handle events that are just related to the runner itself, independent of any runs
                        case schemas.ApiRunnerEventRead.event_discriminator:
                            await self._handle_runner_events(events, update_events_bundle)
                            break
                        # handle events related to a run that is currently being executed
                        case (
                            schemas.ApiRunEventStartRunRead.event_discriminator
                            | schemas.ApiRunEventRead.event_discriminator
                        ):
                            await self._handle_general_run_events(events, update_events_bundle)
                            break
                        # handle events notifying us that proxy on other runner became ready
                        case schemas.ApiProxyStateChangeEventRead.event_discriminator:
                            await self._handle_proxy_ready_run_events(events)
                            break
                        case _:
                            LOGGER.error(f"encountered not yet handled event type {key}")

                if not update_events_bundle.empty():
                    await self._rc.update_events(update_events_bundle)

                await asyncio.sleep(self._polling_delay_sec)

        except asyncio.CancelledError:
            LOGGER.error(f"cancelled event handling loop")
            await self._cancel_all_tasks()

        except Exception:
            await self._cancel_all_tasks()
            trace = traceback.format_exc()
            LOGGER.error(f"an error occured while running: {trace}")

    async def run(self) -> None:
        LOGGER.info("STARTED RUNNER")
        LOGGER.debug(
            f" runner params: base_url={self._base_url}, workdir={self._workdir}, namespace={self._namespace}, ident={self._ident}, polling_delay_sec={self._polling_delay_sec}"
        )

        try:
            await self._handle_events()
        except Exception as exc:
            LOGGER.error(f"fatal error {exc}")
            raise exc

        LOGGER.info("TERMINATED RUNNER")


async def amain():
    runner = Runner(
        base_url=settings.runner_settings().base_url,
        workdir=pathlib.Path("./runner-work").resolve(),
        namespace=settings.runner_settings().namespace,
        ident=settings.runner_settings().runner_id,
        polling_delay_sec=settings.runner_settings().polling_delay_sec,
    )

    await runner.run()


def setup_logger() -> logging.Logger:
    level = settings.RunnerSettings().log_level
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
