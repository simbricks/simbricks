from __future__ import annotations

import abc
import asyncio
import datetime
import json
import logging
import pathlib
import traceback
import typing
import uuid

from simbricks.client.namespace import (
    EventFromRunner_U,
    EventToRunner_U,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.models import (
    Fragment,
    FragmentStateChange,
    KillRunReq,
    # events to runner
    ProxyChangedState,
    ProxyOutput,
    ProxyStateChange,
    RunComponentState,
    RunFragment,
    RunState,
    SimulationSigusr1,
    SimulatorChangedState,
    SimulatorOutput,
    # events from runner
    SimulatorStateChange,
    StartRunReq,
)
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.system import base as sys_base
from simbricks.runner import artifacts as runner_artifacts
from simbricks.runner import framing
from simbricks.runtime import simulation_executor as sim_exec
from simbricks.utils import artifatcs as utils_art

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import proxy as inst_proxy


class RunnerSimulationExecutorCallbacks(sim_exec.SimulationExecutorCallbacks):
    def __init__(
        self,
        instantiation: inst_base.Instantiation,
        send_queue: asyncio.Queue[EventFromRunner_U],
        run_id: str,
    ):
        super().__init__(instantiation)
        self._instantiation = instantiation
        self._send_queue = send_queue
        self._run_id: str = run_id

    # ---------------------------------------
    # Callbacks related to whole simulation -
    # ---------------------------------------

    async def simulation_prepare_cmd_start(self, cmd: str) -> None:
        LOGGER.debug(f"+ [prepare] {cmd}")
        # TODO Send executed prepare command to backend

    async def simulation_prepare_cmd_stdout(self, cmd: str, lines: list[str]) -> None:
        await super().simulation_prepare_cmd_stdout(cmd, lines)
        for line in lines:
            LOGGER.debug(f"[prepare] {line}")
        # TODO Send simulation prepare output to backend

    async def simulation_prepare_cmd_stderr(self, cmd: str, lines: list[str]) -> None:
        await super().simulation_prepare_cmd_stderr(cmd, lines)
        for line in lines:
            LOGGER.debug(f"[prepare] {line}")
        # TODO Send simulation prepare output to backend

    # -----------------------------
    # Simulator-related callbacks -
    # -----------------------------

    async def _send_state_simulator_event(
        self,
        simulator_id: int,
        sim_name: str,
        state: RunComponentState,
        cmd: str | None = None,
    ) -> None:
        event = SimulatorStateChange(
            run_id=self._run_id,
            simulator_id=simulator_id,
            state=state,
            simulator_name=sim_name,
            command=cmd,
        )
        await self._send_queue.put(event)

    async def _send_out_simulator_events(
        self, simulator_id: int, lines: list[str], stderr: bool
    ) -> None:
        for line in lines:
            event = SimulatorOutput(
                run_id=self._run_id,
                simulator_id=simulator_id,
                output=line,
                is_stderr=stderr,
                produced_at=datetime.datetime.now(),
            )
            await self._send_queue.put(event)

    async def simulator_prepare_started(self, sim: sim_base.Simulator, cmd: str) -> None:
        LOGGER.debug(f"+ [{sim.full_name()}] {cmd}")
        await self._send_state_simulator_event(
            sim.id(), sim.full_name(), RunComponentState.PREPARING, cmd
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
            sim.id(), sim.full_name(), RunComponentState.STARTING, cmd
        )

    async def simulator_ready(self, sim: sim_base.Simulator) -> None:
        LOGGER.debug(f"- [{sim.full_name()}] is ready")
        # TODO: Due to coroutine scheduling, simulator might have already been terminated and
        # simulator_exited was already called
        await self._send_state_simulator_event(
            sim.id(), sim.full_name(), state=RunComponentState.RUNNING
        )

    async def simulator_exited(self, sim: sim_base.Simulator, exit_code: int) -> None:
        LOGGER.debug(f"- [{sim.full_name()}] exited with code {exit_code}")
        # Report exit code to backend. Right now, we just do this as a line of console output.
        await self._send_out_simulator_events(sim.id(), [f"exited with code {exit_code}"], False)
        await self._send_state_simulator_event(
            sim.id(), sim.full_name(), state=RunComponentState.TERMINATED
        )

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
        state: RunComponentState,
        proxy_ip: str | None,
        proxy_port: int | None,
        proxy_cmd: str | None = None,
    ) -> None:
        assert proxy_ip is not None and proxy_port is not None
        event = ProxyStateChange(
            run_id=self._run_id,
            proxy_name=proxy_name,
            proxy_id=proxy_id,
            state=state,
            ip=proxy_ip,
            port=proxy_port,
            command=proxy_cmd,
        )
        await self._send_queue.put(event)

    async def _send_out_proxy_events(self, proxy_id: int, lines: list[str], stderr: bool) -> None:
        for line in lines:
            event = ProxyOutput(
                run_id=self._run_id,
                proxy_id=proxy_id,
                output=line,
                is_stderr=stderr,
                produced_at=datetime.datetime.now(),
            )
            await self._send_queue.put(event)

    async def proxy_started(self, proxy: inst_proxy.Proxy, cmd: str) -> None:
        LOGGER.debug(f"+ [{proxy.name}] {cmd}")
        await self._send_state_proxy_event(
            proxy.id(),
            proxy.name,
            RunComponentState.STARTING,
            proxy._ip,
            proxy._port,
            proxy_cmd=cmd,
        )

    async def proxy_ready(self, proxy: inst_proxy.Proxy) -> None:
        LOGGER.debug(f"[{proxy.name}] has started successfully")
        await self._send_state_proxy_event(
            proxy.id(),
            proxy.name,
            RunComponentState.RUNNING,
            proxy._ip,
            proxy._port,
        )

    async def proxy_exited(self, proxy: inst_proxy.Proxy, exit_code: int) -> None:
        LOGGER.debug(f"- [{proxy.name}] exited with code {exit_code}")
        await self._send_out_proxy_events(proxy.id(), [f"exited with code {exit_code}"], False)
        await self._send_state_proxy_event(
            proxy.id(), proxy.name, RunComponentState.TERMINATED, proxy._ip, proxy._port
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
        run_id: str,
        inst: inst_base.Instantiation,
        callbacks: RunnerSimulationExecutorCallbacks,
        runner: sim_exec.SimulationExecutor,
        run_fragment: RunFragment,
    ) -> None:
        self.run_id: str = run_id
        self.inst: inst_base.Instantiation = inst
        self.callbacks: RunnerSimulationExecutorCallbacks = callbacks
        self.cancelled: bool = False
        self.runner: sim_exec.SimulationExecutor = runner
        self.run_fragment = run_fragment
        self.exec_task: asyncio.Task | None = None


class FragmentRunner(abc.ABC):
    def __init__(
        self,
        base_url: str,
        workdir: pathlib.Path,
        global_input_dir: pathlib.Path | None,
        namespace: str,
        ident: int,
        polling_delay_sec: float,
        sending_delay_sec: float,
        proxy_host_ip: str,
        verbose: bool,
        output_artifact_relative: bool,
        event_batch_size: int,
    ):
        self._base_url: str = base_url
        self._workdir: pathlib.Path = workdir.resolve()
        self._global_input_dir: pathlib.Path | None = global_input_dir
        self._polling_delay_sec: float = polling_delay_sec
        self._sending_delay_sec: float = sending_delay_sec
        self._namespace: str = namespace
        self._ident: int = ident
        self._proxy_host_ip: str = proxy_host_ip
        self._verbose: bool = verbose
        self._output_artifact_relative: bool = output_artifact_relative
        self.event_batch_size = event_batch_size if event_batch_size > 0 else 1

        self._send_event_queue = asyncio.Queue[EventFromRunner_U]()

        self._channel = framing.FrameChannel(self.read, self.write)
        self._artifact_sink = runner_artifacts.RelayArtifactSink(self._channel)
        self._artifact_receiver = runner_artifacts.ArtifactReceiver(self._workdir / "tmp")
        #: Input artifacts that arrived, waiting for the run they belong to.
        self._input_artifacts: dict[
            tuple[str, runner_artifacts.ArtifactKind], runner_artifacts.Artifact
        ] = {}

        self._run_map: dict[str, Run] = {}

        self._worker_tasks: list[asyncio.Task] = []

    @abc.abstractmethod
    async def connect(self) -> None:
        pass

    @abc.abstractmethod
    async def read(self, length: int) -> bytes:
        pass

    @abc.abstractmethod
    async def write(self, data: bytes) -> None:
        pass

    async def send_events(self, events: list[EventFromRunner_U]) -> None:
        await self._channel.send(framing.EventFrame.pack(events))

    async def _enqueue_fragment_state_change(
        self, run_id: str, run_fragment_id: str, run_state: RunState
    ) -> None:
        event = FragmentStateChange(
            run_id=run_id,
            run_fragment_id=run_fragment_id,
            run_state=run_state,
            produced_at=datetime.datetime.now(),
        )
        await self._send_event_queue.put(event)

    async def _assemble_inst(self, start_event: StartRunReq) -> inst_base.Instantiation:
        LOGGER.debug(f"fetch and assemble instantiation related to run {start_event.run_id}")

        # For now we expect to always have exactly one fragment per runner
        if len(start_event.fragments) != 1:
            raise RuntimeError("There must be exactly one fragment assigned to a runner")

        run_workdir = self._workdir / f"run-{start_event.run_id}-{start_event.fragments[0].id}"
        if run_workdir.exists():
            LOGGER.warning(
                f"the directory {run_workdir} already exists, will create a new one using a uuid"
            )
            run_workdir = self._workdir / f"run-{start_event.run_id}-{str(uuid.uuid4())}"
        run_workdir.mkdir(parents=True)

        assert isinstance(start_event.system.sb_json, str)
        assert isinstance(start_event.simulation.sb_json, str)
        assert isinstance(start_event.inst.sb_json, str)
        system = sys_base.System.fromJSON(json.loads(start_event.system.sb_json))
        simulation = sim_base.Simulation.fromJSON(
            system, json.loads(start_event.simulation.sb_json)
        )
        inst = inst_base.Instantiation.fromJSON(simulation, json.loads(start_event.inst.sb_json))

        # build inst fragments map
        # NOTE: do not use the parsed simbricks instantiation
        fragment_map: dict[str, Fragment] = {}
        assert isinstance(start_event.inst.fragments, list)
        for frag in start_event.inst.fragments:
            frag: Fragment = frag
            assert isinstance(frag, Fragment) and isinstance(frag.id, str)
            fragment_map[frag.id] = frag

        env = inst_base.InstantiationEnvironment(run_workdir, self._global_input_dir)
        inst.env = env

        assert len(start_event.fragments) == 1
        req_frag_id = start_event.fragments[0].fragment_id
        assert isinstance(req_frag_id, str)
        req_frag = fragment_map[req_frag_id]
        assert isinstance(req_frag.object_id, int)
        inst.assigned_fragment = inst.get_fragment(req_frag.object_id)

        # retrieve input artifacts
        input_artifacts_dir = inst.env.input_artifacts_dir()
        pathlib.Path(input_artifacts_dir).mkdir(parents=True, exist_ok=True)

        # The main runner streams these ahead of the start event, so by the time
        # we get here they have already arrived and are waiting on disk.
        if inst.input_artifact_paths:
            self._unpack_input_artifact(
                start_event.run_id,
                runner_artifacts.ArtifactKind.INSTANTIATION_INPUT,
                input_artifacts_dir,
            )

        if inst.assigned_fragment.input_artifact_paths:
            self._unpack_input_artifact(
                start_event.run_id,
                runner_artifacts.ArtifactKind.FRAGMENT_INPUT,
                input_artifacts_dir,
            )

        return inst

    def _unpack_input_artifact(
        self, run_id: str, kind: runner_artifacts.ArtifactKind, dest_dir: str
    ) -> None:
        artifact = self._input_artifacts.pop((run_id, kind), None)
        if artifact is None:
            raise RuntimeError(f"no {kind.value} artifact arrived for run {run_id}")
        try:
            utils_art.unpack_artifact(str(artifact.path), dest_dir)
        finally:
            artifact.path.unlink(missing_ok=True)

    def _discard_input_artifacts(self, run_id: str) -> None:
        """Drop this run's input artifacts that arrived but were never unpacked."""
        for key in [key for key in self._input_artifacts if key[0] == run_id]:
            self._input_artifacts.pop(key).path.unlink(missing_ok=True)

    async def _prepare_run(self, start_event: StartRunReq) -> Run:
        LOGGER.debug(f"prepare run {start_event.run_id}")

        inst = await self._assemble_inst(start_event)
        callbacks = RunnerSimulationExecutorCallbacks(
            inst, self._send_event_queue, start_event.run_id
        )
        runner = sim_exec.SimulationExecutor(inst, callbacks, self._verbose, self._proxy_host_ip)
        await runner.prepare()

        assert len(start_event.fragments) == 1
        run = Run(start_event.run_id, inst, callbacks, runner, start_event.fragments[0])
        return run

    async def _start_run(self, run: Run) -> None:
        assert isinstance(run.run_fragment.id, str)
        sim_task = None
        try:
            LOGGER.info(f"start run {run.run_id}")

            await self._enqueue_fragment_state_change(
                run.run_id, run.run_fragment.id, RunState.RUNNING
            )

            # TODO: allow for proper checkpointing run
            sim_task = asyncio.create_task(run.runner.run())
            res = await sim_task

            output_path = run.inst.env.get_simulation_output_path()
            res.dump(outpath=output_path)  # TODO: FIXME

            if run.inst.assigned_fragment.output_artifact_paths:
                await self._artifact_sink.produce(
                    utils_art.ArtifactInfo(
                        kind=utils_art.ArtifactKind.OUTPUT,
                        name=run.inst.assigned_fragment.output_artifact_name,
                        run_id=run.run_id,
                        run_fragment_id=run.run_fragment.id,
                    ),
                    paths_to_include=run.inst.assigned_fragment.output_artifact_paths,
                    base_path=pathlib.Path(run.inst.env.work_dir()),
                    # Outside the work directory, otherwise the artifact ends up
                    # inside the very tree it is packing.
                    staging_dir=self._workdir,
                    check_relative=self._output_artifact_relative,
                )

            status = RunState.ERROR if res.failed() else RunState.COMPLETED
            await self._enqueue_fragment_state_change(run.run_id, run.run_fragment.id, status)

            await run.runner.cleanup()

            LOGGER.info(f"finished run {run.run_id}")

        except asyncio.CancelledError:
            LOGGER.debug("_start_sim handle cancelled error")

            if sim_task:
                sim_task.cancel()

            await self._enqueue_fragment_state_change(
                run.run_id, run.run_fragment.id, RunState.CANCELLED
            )

            LOGGER.info(f"cancelled execution of run {run.run_id}")

        except Exception:
            LOGGER.debug("_start_sim handle error")
            if sim_task:
                sim_task.cancel()

            await self._enqueue_fragment_state_change(
                run.run_id, run.run_fragment.id, RunState.ERROR
            )

            LOGGER.error(f"error while executing run {run.run_id}: {traceback.format_exc()}")

    async def _cancel_all_tasks(self) -> None:
        for _, run in self._run_map.items():
            if run.exec_task is None or run.exec_task.done():
                continue

            run.exec_task.cancel()
            try:
                await run.exec_task
            except asyncio.CancelledError:
                pass

    async def _handle_kill_run(self, event: KillRunReq) -> None:
        if event.run_id and event.run_id not in self._run_map:
            return

        run = self._run_map[event.run_id]
        if run.exec_task is None:
            return
        run.exec_task.cancel()
        await run.exec_task

        LOGGER.debug(f"executed kill to cancel execution of run {event.run_id}")
        LOGGER.info(f"handled run related event {event.id}")

    async def _handle_sigusr1(self, event: SimulationSigusr1) -> None:
        if not event.run_id or event.run_id not in self._run_map:
            return

        run = self._run_map[event.run_id]
        await run.runner.sigusr1()

        LOGGER.debug(f"send sigusr1 to run {event.run_id}")
        LOGGER.info(f"handled run related event {event.id}")

    async def _handle_start_run(self, event: StartRunReq) -> None:
        if event.run_id in self._run_map:
            LOGGER.debug(f"cannot start run, run with id {event.run_id} is already being executed")
            return

        try:
            # The await here is deliberate, we want to make sure that we block here
            # and do not poll for / process further events before the run is fully
            # set up.

            # For example, we need this property when dealing with distributed
            # simulations. Other runners might send events to us, so we need the
            # necessary data structures to handle them to be fully set up.
            run = await self._prepare_run(event)

            run.exec_task = asyncio.create_task(self._start_run(run=run))
            self._run_map[event.run_id] = run
            LOGGER.debug(f"started execution of run {event.run_id}")

        except Exception:
            trace = traceback.format_exc()
            LOGGER.error(f"could not prepare run {event.run_id}: {trace}")

            assert len(event.fragments) == 1
            frag_id = event.fragments[0].id
            assert isinstance(frag_id, str)
            await self._enqueue_fragment_state_change(event.run_id, frag_id, RunState.ERROR)
        finally:
            # A no-op once the run is set up, since _assemble_inst takes every
            # artifact it expects. Anything left belongs to a run that failed.
            self._discard_input_artifacts(event.run_id)

        LOGGER.info(f"handled run related event {event.id}")

    async def _handle_proxy_ready_run_event(self, event: ProxyChangedState) -> None:
        if event.state != RunComponentState.RUNNING:
            return

        run_id = event.run_id
        if run_id and run_id not in self._run_map:
            return

        run = self._run_map[run_id]
        await run.runner.mark_external_proxies_running(event.proxy_id, event.ip, event.port)
        LOGGER.debug(f"processed ProxyChangedState for proxy {event.proxy_id} and marked it ready")

    async def _handle_simulator_state_change_event(self, event: SimulatorChangedState) -> None:
        run_id = event.run_id
        if run_id not in self._run_map:
            return

        if event.state == RunComponentState.TERMINATED:
            run = self._run_map[run_id]
            await run.runner.mark_simulator_terminated(event.simulator_id)
            LOGGER.debug(f"marked simulator {event.simulator_id} as terminated")

        return

    async def _handle_events(self) -> None:
        while True:
            frame = await self._channel.receive()

            if isinstance(frame, framing.ArtifactFrame):
                artifact = self._artifact_receiver.handle_frame(frame)
                if artifact is not None:
                    key = (artifact.info.run_id, artifact.info.kind)
                    previous = self._input_artifacts.pop(key, None)
                    if previous is not None:
                        LOGGER.warning(f"replacing {key[1].value} artifact for run {key[0]}")
                        previous.path.unlink(missing_ok=True)
                    self._input_artifacts[key] = artifact
                continue

            # This connection only ever receives commands from the main runner;
            # EventFrame.unpack' return type is broader.
            assert isinstance(frame, framing.EventFrame)
            events = typing.cast(list[EventToRunner_U], frame.unpack())

            LOGGER.debug(f"{len(events)} events fetched")

            for event in events:
                match event:
                    case KillRunReq():
                        await self._handle_kill_run(event)
                    case SimulationSigusr1():
                        await self._handle_sigusr1(event)
                    case StartRunReq():
                        await self._handle_start_run(event)
                    case ProxyChangedState():
                        await self._handle_proxy_ready_run_event(event)
                    case SimulatorChangedState():
                        await self._handle_simulator_state_change_event(event)
                    case _:
                        LOGGER.error(f"encountered not yet handled event type {event}")

    async def _worker_loop(self):

        # TODO: Is there now a better place to do this?
        while True:
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
            events = [await self._send_event_queue.get()]
            await asyncio.sleep(self._sending_delay_sec)
            while not self._send_event_queue.empty():
                events.append(self._send_event_queue.get_nowait())
            for i in range(0, len(events), self.event_batch_size):
                await self.send_events(events[i : i + self.event_batch_size])

    async def run(self) -> None:
        LOGGER.info("STARTED FRAGMENT EXECUTOR")
        LOGGER.debug(
            f"fragment executor params: base_url={self._base_url}, workdir={self._workdir}, namespace={self._namespace}, ident={self._ident}, polling_delay_sec={self._polling_delay_sec}"
        )

        try:
            await self.connect()
        except Exception:
            LOGGER.error("failed to connect to runner")
            raise

        workers: list[asyncio.Task] = []
        try:
            workers.append(asyncio.create_task(self._send_loop()))
            workers.append(asyncio.create_task(self._worker_loop()))
            workers.append(asyncio.create_task(self._handle_events()))
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            LOGGER.error("cancelled event handling loop")
            for worker in workers:
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    LOGGER.debug(f"cancelled worker task {worker.get_name()}")
            await self._cancel_all_tasks()

        except Exception:
            await self._cancel_all_tasks()
            trace = traceback.format_exc()
            LOGGER.error(f"an error occured while running: {trace}")

        LOGGER.info("TERMINATED RUNNER")


LOGGER: logging.Logger = logging.getLogger(__name__)
