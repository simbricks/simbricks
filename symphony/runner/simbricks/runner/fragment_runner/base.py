from __future__ import annotations

import abc
import asyncio
import json
import logging
import pathlib
import traceback
import typing
import uuid

from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.system import base as sys_base
from simbricks.runner import settings
from simbricks.runner import utils as runner_utils
from simbricks.runtime import simulation_executor as sim_exec
from simbricks.schemas import base as schemas
from simbricks.utils import artifatcs as utils_art

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import proxy as inst_proxy


class RunnerSimulationExecutorCallbacks(sim_exec.SimulationExecutorCallbacks):

    def __init__(
        self,
        instantiation: inst_base.Instantiation,
        send_queue: asyncio.Queue[tuple[schemas.ApiEventType, schemas.ApiEventBundle]],
        run_id: int,
    ):
        super().__init__(instantiation)
        self._instantiation = instantiation
        self._send_queue = send_queue
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
            run_id=self._run_id,
            simulator_id=simulator_id,
            simulator_state=state,
            simulator_name=sim_name,
            command=cmd,
        )

        event_bundle = schemas.ApiEventBundle()
        event_bundle.add_event(event)
        await self._send_queue.put((schemas.ApiEventType.ApiEventCreate, event_bundle))

    async def _send_out_simulator_events(
        self, simulator_id: int, lines: list[str], stderr: bool
    ) -> None:
        event_bundle = schemas.ApiEventBundle[schemas.ApiSimulatorOutputEventCreate]()
        for line in lines:
            event = schemas.ApiSimulatorOutputEventCreate(
                run_id=self._run_id,
                simulator_id=simulator_id,
                output=line,
                is_stderr=stderr,
            )
            event_bundle.add_event(event)

        await self._send_queue.put((schemas.ApiEventType.ApiEventCreate, event_bundle))

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
        proxy_name: str,
        state: schemas.RunComponentState,
        proxy_ip: str,
        proxy_port: int,
        proxy_cmd: str | None = None,
    ) -> None:
        event = schemas.ApiProxyStateChangeEventCreate(
            run_id=self._run_id,
            proxy_name=proxy_name,
            proxy_id=proxy_id,
            proxy_state=state,
            proxy_ip=proxy_ip,
            proxy_port=proxy_port,
            command=proxy_cmd,
        )

        event_bundle = schemas.ApiEventBundle()
        event_bundle.add_event(event)
        await self._send_queue.put((schemas.ApiEventType.ApiEventCreate, event_bundle))

    async def _send_out_proxy_events(self, proxy_id: int, lines: list[str], stderr: bool) -> None:
        event_bundle = schemas.ApiEventBundle[schemas.ApiProxyOutputEventCreate]()
        for line in lines:
            event = schemas.ApiProxyOutputEventCreate(
                run_id=self._run_id,
                proxy_id=proxy_id,
                output=line,
                is_stderr=stderr,
            )
            event_bundle.add_event(event)

        await self._send_queue.put((schemas.ApiEventType.ApiEventCreate, event_bundle))

    async def proxy_started(self, proxy: inst_proxy.Proxy, cmd: str) -> None:
        LOGGER.debug(f"+ [{proxy.name}] {cmd}")

        await self._send_state_proxy_event(
            proxy.id(),
            proxy.name,
            schemas.RunComponentState.STARTING,
            proxy._ip,
            proxy._port,
            proxy_cmd=cmd,
        )

    async def proxy_ready(self, proxy: inst_proxy.Proxy) -> None:
        LOGGER.debug(f"[{proxy.name}] has started successfully")
        await self._send_state_proxy_event(
            proxy.id(),
            proxy.name,
            schemas.RunComponentState.RUNNING,
            proxy._ip,
            proxy._port,
        )

    async def proxy_exited(self, proxy: inst_proxy.Proxy, exit_code: int) -> None:
        LOGGER.debug(f"- [{proxy.name}] exited with code {exit_code}")
        await self._send_out_proxy_events(proxy.id(), [f"exited with code {exit_code}"], False)
        await self._send_state_proxy_event(
            proxy.id(), proxy.name, schemas.RunComponentState.TERMINATED, proxy._ip, proxy._port
        )

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


class FragmentRunner(abc.ABC):

    def __init__(
        self, base_url: str,
        workdir: str,
        namespace: str,
        ident: int,
        polling_delay_sec: int,
        runner_ip: str,
    ):
        self._base_url: str = base_url
        self._workdir: pathlib.Path = pathlib.Path(workdir).resolve()
        self._polling_delay_sec: int = polling_delay_sec
        self._namespace: str = namespace
        self._ident: int = ident
        self._runner_ip: str = runner_ip

        self._send_event_queue = asyncio.Queue[
            tuple[schemas.ApiEventType, schemas.ApiEventBundle]
        ]()

        self._run_map: dict[int, Run] = {}

        self._worker_tasks: list[asyncio.Task] = []

    @abc.abstractmethod
    async def read(self, length: int) -> bytes:
        pass

    @abc.abstractmethod
    async def write(self, data: bytes) -> None:
        pass

    async def send_events(
        self, events: schemas.ApiEventBundle, event_type: schemas.ApiEventType
    ) -> None:
        await runner_utils.send_events(self.write, events, event_type)

    async def get_events(self) -> tuple[schemas.ApiEventType, schemas.ApiEventBundle]:
        return await runner_utils.get_events(self.read)
    
    async def _assemble_inst(
        self, run_id: int, start_event: schemas.ApiRunEventStartRunRead
    ) -> inst_base.Instantiation:
        LOGGER.debug(f"fetch and assemble instantiation related to run {run_id}")

        # For now we expect to always have exactly one fragment per runner
        if len(start_event.fragments) != 1:
            raise RuntimeError("There must be exactly one fragment assigned to a runner")

        run_workdir = self._workdir / f"run-{run_id}"
        if run_workdir.exists():
            LOGGER.warning(
                f"the directory {run_workdir} already exists, will create a new one using a uuid"
            )
            run_workdir = self._workdir / f"run-{run_id}-{str(uuid.uuid4())}"
        run_workdir.mkdir(parents=True)

        if (
            start_event.inst is None
            or start_event.system is None
            or start_event.simulation is None
        ):
            raise RuntimeError("start event must contain system, simulation, and instantiation")

        system = sys_base.System.fromJSON(json.loads(start_event.system))
        simulation = sim_base.Simulation.fromJSON(system, json.loads(start_event.simulation))
        inst = inst_base.Instantiation.fromJSON(simulation, json.loads(start_event.inst))

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

        inst = await self._assemble_inst(run_id, start_event)
        callbacks = RunnerSimulationExecutorCallbacks(inst, self._send_event_queue, run_id)
        runner = sim_exec.SimulationExecutor(
            inst, callbacks, settings.RunnerSettings().verbose, self._runner_ip
        )
        await runner.prepare()

        run = Run(run_id=run_id, inst=inst, runner=runner, callbacks=callbacks)
        return run

    async def _start_run(self, run: Run) -> None:
        sim_task = None
        try:
            LOGGER.info(f"start run {run.run_id}")

            event = schemas.ApiRunFragmentStateEventCreate(
                run_id=run.run_id,
                fragment_id=run.inst.assigned_fragment.id(),
                run_state=schemas.RunState.RUNNING
            )
            event_bundle = schemas.ApiEventBundle()
            event_bundle.add_event(event)
            await self._send_event_queue.put((schemas.ApiEventType.ApiEventCreate, event_bundle))

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
                # TODO: send artifact to runner using artifact event
                await self._sb_client.set_run_artifact(run.run_id, run.inst.artifact_name)

            status = schemas.RunState.ERROR if res.failed() else schemas.RunState.COMPLETED
            event = schemas.ApiRunFragmentStateEventCreate(
                run_id=run.run_id,
                fragment_id=run.inst.assigned_fragment.id(),
                run_state=status
            )
            event_bundle = schemas.ApiEventBundle()
            event_bundle.add_event(event)
            await self._send_event_queue.put((schemas.ApiEventType.ApiEventCreate, event_bundle))

            await run.runner.cleanup()

            LOGGER.info(f"finished run {run.run_id}")

        except asyncio.CancelledError:
            LOGGER.debug("_start_sim handle cancelled error")
            if sim_task:
                sim_task.cancel()
            event = schemas.ApiRunFragmentStateEventCreate(
                run_id=run.run_id,
                fragment_id=run.inst.assigned_fragment.id(),
                run_state=schemas.RunState.CANCELLED
            )
            event_bundle = schemas.ApiEventBundle()
            event_bundle.add_event(event)
            await self._send_event_queue.put((schemas.ApiEventType.ApiEventCreate, event_bundle))
            LOGGER.info(f"cancelled execution of run {run.run_id}")

        except Exception as ex:
            LOGGER.debug("_start_sim handle error")
            if sim_task:
                sim_task.cancel()
            event = schemas.ApiRunFragmentStateEventCreate(
                run_id=run.run_id,
                fragment_id=run.inst.assigned_fragment.id(),
                run_state=schemas.RunState.ERROR
            )
            event_bundle = schemas.ApiEventBundle()
            event_bundle.add_event(event)
            await self._send_event_queue.put((schemas.ApiEventType.ApiEventCreate, event_bundle))
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
                case schemas.RunEventType.SIMULATION_STATUS:
                    if not run_id or not run_id in self._run_map:
                        update.event_status = schemas.ApiEventStatus.CANCELLED
                    else:
                        run = self._run_map[run_id]
                        await run.runner.sigusr1()
                        update.event_status = schemas.ApiEventStatus.COMPLETED
                        LOGGER.debug(f"send sigusr1 to run {run_id}")
                case schemas.RunEventType.START_RUN:
                    assert event.event_discriminator == "ApiRunEventStartRunRead"
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
                            assert len(event.fragments) == 1
                            state_event = schemas.ApiRunFragmentStateEventCreate(
                                run_id=run.run_id,
                                fragment_id=event.fragments[0][0],
                                run_state=schemas.RunState.ERROR
                            )
                            event_bundle = schemas.ApiEventBundle()
                            event_bundle.add_event(state_event)
                            await self._send_event_queue.put((schemas.ApiEventType.ApiEventCreate, event_bundle))
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
            await run.runner.mark_external_proxies_running(
                event.proxy_id, event.proxy_ip, event.proxy_port
            )
            LOGGER.debug(
                f"processed ApiProxyReadyRunEventRead for proxy {event.proxy_id} and marked it ready"
            )

    async def _handle_simulator_state_change_events(
        self, events: list[schemas.ApiSimulatorStateChangeEventRead]
    ) -> None:
        # TODO: FIXME the same applies here as for _handle_proxy_ready_run_events
        for event in events:
            run_id = event.run_id
            if run_id not in self._run_map:
                continue

            run = self._run_map[run_id]
            await run.runner.mark_simulator_terminated(event.simulator_id)
            LOGGER.debug(f"marked simulator {event.simulator_id} as terminated")

    async def _handle_events(self) -> None:
        while True:
            event_type, event_bundle = await self.get_events()

            if event_type != schemas.ApiEventType.ApiEventRead:
                LOGGER.warning(f"received events of unexpected type {event_type.value}")
                continue

            LOGGER.debug(f"events fetched ({len(event_bundle.events)}): {event_bundle.events}")

            update_events_bundle = schemas.ApiEventBundle[schemas.ApiEventUpdate_U]()
            for key, events in event_bundle.events.items():
                match key:
                    # handle events related to a run that is currently being executed
                    case ("ApiRunEventStartRunRead" | "ApiRunEventRead"):
                        await self._handle_general_run_events(events, update_events_bundle)
                    # handle events notifying us that proxy on other runner became ready
                    case "ApiProxyStateChangeEventRead":
                        await self._handle_proxy_ready_run_events(events)
                    case "ApiSimulatorStateChangeEventRead":
                        await self._handle_simulator_state_change_events(events)
                    case _:
                        LOGGER.error(f"encountered not yet handled event type {key}")

            if not update_events_bundle.empty():
                await self._send_event_queue.put(
                    (schemas.ApiEventType.ApiEventUpdate, update_events_bundle)
                )

    async def _worker_loop(self):
        while True:
            # fetch all events not handled yet
            event_query_bundle = schemas.ApiEventBundle[schemas.ApiEventQuery_U]()

            if self._run_map:
                # query events indicating that proxies are now ready
                state_change_q = schemas.ApiProxyStateChangeEventQuery(
                    run_ids=list(self._run_map.keys()),
                    proy_states=[schemas.RunComponentState.RUNNING],
                )
                event_query_bundle.add_event(state_change_q)

                for id, run in self._run_map.items():
                    simulator_term_q = schemas.ApiSimulatorStateChangeEventQuery(
                        run_ids=[id],
                        simulator_ids=list(run.runner._wait_sims.keys()),
                        simulator_states=[schemas.RunComponentState.TERMINATED],
                    )
                    event_query_bundle.add_event(simulator_term_q)

            await self._send_event_queue.put(
                (schemas.ApiEventType.ApiEventQuery, event_query_bundle)
            )

            for run_id in list(self._run_map.keys()):
                run = self._run_map[run_id]
                # check if run finished and cleanup map
                if run.exec_task and run.exec_task.done():
                    run = self._run_map.pop(run_id)
                    LOGGER.debug(f"removed run {run_id} from run_map")
                    assert run_id not in self._run_map
                    continue

            await asyncio.sleep(self._polling_delay_sec)

    async def _send_loop(self):
        while True:
            event_type, event_bundle = await self._send_event_queue.get()
            await self.send_events(event_bundle, event_type)

    async def run(self) -> None:
        LOGGER.info("STARTED FRAGMENT EXECUTOR")
        LOGGER.debug(
            f"fragment executor params: base_url={self._base_url}, workdir={self._workdir}, namespace={self._namespace}, ident={self._ident}, polling_delay_sec={self._polling_delay_sec}"
        )

        try:
            await self._handle_events()
        except Exception as exc:
            LOGGER.error(f"fatal error {exc}")
            raise exc

        try:
            workers = []
            workers.append(asyncio.create_task(self._send_loop()))
            workers.append(asyncio.create_task(self._worker_loop()))
            workers.append(asyncio.create_task(self._handle_events()))
            #TODO: need to properly handle cancellation here
            asyncio.gather(*workers)
        except asyncio.CancelledError:
            LOGGER.error(f"cancelled event handling loop")
            await self._cancel_all_tasks()

        except Exception:
            await self._cancel_all_tasks()
            trace = traceback.format_exc()
            LOGGER.error(f"an error occured while running: {trace}")

        LOGGER.info("TERMINATED RUNNER")


def setup_logger() -> logging.Logger:
    level = settings.RunnerSettings().log_level
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger(__name__)
    return logger


LOGGER = setup_logger()