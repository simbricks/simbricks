from __future__ import annotations

import abc
import asyncio
import base64
import itertools
import io
import json
import logging
import traceback
import typing as tp
import yaml

from simbricks import client
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.system import base as sys_base
from simbricks.runner.main_runner import settings
from simbricks.runner.main_runner.plugins import plugin
from simbricks.runner.main_runner.plugins import plugin_loader
from simbricks.runner import utils as runner_utils
from simbricks.telemetry.base import setup_telemetry
from simbricks.client.namespace import EventToRunner_U, EventFromRunner_U
from simbricks.client.openapi.client.python.sim_bricks_api_client.models import (
    Fragment,
    RunnerTag,
    RunState,
    PaginationLinks,
    # events to runner
    KillRunReq,
    RunnerHeartbeatReq,
    StartRunReq,
    SimulationSigusr1,
    SimulatorChangedState,
    ProxyChangedState,
    # events from runner
    RunnerStarted,
    RunnerHeartbeat,
    RunStatus,
    FragmentStateChange,
    FragmentOutputArtifact,
    SimulatorStateChange,
    SimulatorOutput,
    ProxyStateChange,
    ProxyOutput,
)


class MainRun:
    def __init__(
        self,
        run_id: str,
        fragment_runner_map: dict[str, FragmentRunner],
    ) -> None:
        self.run_id = run_id
        self.fragment_runner_map = fragment_runner_map
        self.cancelled: bool = False

        self.fragment_run_state: dict[str, RunState] = {}
        for fragment in fragment_runner_map:
            self.fragment_run_state[fragment] = RunState.SPAWNED


class FragmentExecutorConfiguration:
    def __init__(
        self, name: str, plugin: type[plugin.FragmentRunnerPlugin], settings: dict[tp.Any, tp.Any]
    ):
        self.name = name
        self.plugin = plugin
        self.settings = settings


class FragmentRunner:
    def __init__(self, name: str, fragment_runner: plugin.FragmentRunnerPlugin):
        self.name = name
        self.fragment_runner = fragment_runner
        self.read_task: asyncio.Task | None = None

    async def stop(self):
        # TODO: remove
        if self.read_task is not None:
            self.read_task.cancel()
            try:
                await self.read_task
            except asyncio.CancelledError:
                pass
        await self.fragment_runner.stop()


class FragmentRunnerEvent:
    def __init__(self, fragment_runner: FragmentRunner, events: list[EventFromRunner_U]):
        self.fragment_runner = fragment_runner
        self.events = events


class MainRunner:

    def __init__(
        self,
        namespace_client: client.NSClient,
        runner_client: client.RunnerClient,
        simbricks_client: client.SimBricksClient,
        ident: str,
        polling_delay_sec: int,
    ):
        self._ident = ident
        self._polling_delay_sec = polling_delay_sec

        self._fragment_executor_configs: dict[str, FragmentExecutorConfiguration] = {}
        self._available_fragment_executors: list[str] = []
        self.fragment_runners: dict[str, set[FragmentRunner]] = {}
        self.fragment_runner_events = asyncio.Queue[FragmentRunnerEvent]()

        self._namespace_client = namespace_client
        self._rc = runner_client
        self._simbricks_client = simbricks_client

        self._run_map: dict[str, MainRun] = {}

    async def _send_events_aggregate_updates(self, event: EventToRunner_U) -> None:
        if not hasattr(event, "run_id") or not isinstance(event.run_id, str) or event.run_id not in self._run_map:
            msg = f"Cannot _send_events_aggregate_updates to run {event.run_id}"
            LOGGER.error(msg)
            raise Exception(msg)

        run = self._run_map[event.run_id]

        # send event to fragment runners
        senders: list[asyncio.Task] = []
        for runner in run.fragment_runner_map.values():
            senders.append(asyncio.create_task(runner.fragment_runner.send_events([event])))

        try:
            await asyncio.gather(*senders)
        except asyncio.CancelledError:
            for sender in senders:
                sender.cancel()
                try:
                    await sender
                except asyncio.CancelledError:
                    pass
            raise

    async def _stop_fragment_runners(self, fragment_runner_map: dict[str, FragmentRunner]):
        stop = []
        for runner in fragment_runner_map.values():
            stop.append(asyncio.create_task(runner.stop()))
            self.fragment_runners[runner.name].remove(runner)

        await asyncio.gather(*stop)

    async def _start_fragment_runner(
        self, name: str, parameters: dict[tp.Any, tp.Any]
    ) -> FragmentRunner:
        assert name in self._fragment_executor_configs
        config = self._fragment_executor_configs[name]
        runner = config.plugin()
        await runner.start(config.settings, parameters)
        fragment_runner = FragmentRunner(name, runner)
        fragment_runner.read_task = asyncio.create_task(
            self._read_fragment_runner_events(fragment_runner)
        )
        self.fragment_runners[name].add(fragment_runner)
        return fragment_runner

    async def _start_run(self, start_run_event: StartRunReq):

        assert start_run_event.system and start_run_event.system.sb_json
        sb_sys = sys_base.System.fromJSON(json.loads(start_run_event.system.sb_json), True)
        assert start_run_event.simulation and start_run_event.simulation.sb_json
        sb_sim = sim_base.Simulation.fromJSON(
            sb_sys, json.loads(start_run_event.simulation.sb_json), True
        )
        assert start_run_event.inst and start_run_event.inst.sb_json
        sb_inst = inst_base.Instantiation.fromJSON(sb_sim, json.loads(start_run_event.inst.sb_json))

        # get parameters from fragments
        parameters_map: dict[int, dict[tp.Any, tp.Any]] = {}
        for fragment in sb_inst.fragments:
            parameters_map[fragment.id()] = fragment._parameters

        # get fragments
        fragment_map: dict[str, Fragment] = {}
        for frag in start_run_event.inst.fragments:
            assert isinstance(frag, Fragment) and isinstance(frag.id, str)
            fragment_map[frag.id] = frag

        # retrieve instantiation input artifacts
        inst_artifact: bytes | None = None
        if sb_inst.input_artifact_paths:
            inst_artifact = await self._simbricks_client.get_inst_input_artifact_raw(
                start_run_event.inst.id
            )

        fragment_runner_map: dict[str, FragmentRunner] = {}
        for rf in start_run_event.fragments:
            assert rf.fragment_id in fragment_map
            frag = fragment_map[rf.fragment_id]

            fragment_executor_tag = frag.fragment_executor_tag

            if fragment_executor_tag is None:
                fragment_executor_tag = self._available_fragment_executors[0]
            elif fragment_executor_tag not in self._fragment_executor_configs:
                await self._stop_fragment_runners(fragment_runner_map)
                raise RuntimeError(f"unsupported fragment runner type {fragment_executor_tag}")

            fragment_runner = await self._start_fragment_runner(
                fragment_executor_tag, parameters_map[frag.object_id]
            )
            assert isinstance(rf.id, str)
            fragment_runner_map[rf.id] = fragment_runner

        run = MainRun(start_run_event.run_id, fragment_runner_map)
        self._run_map[start_run_event.run_id] = run

        senders: list[asyncio.Task] = []
        for rf in start_run_event.fragments:
            start_fragment_event = StartRunReq(
                run_id=start_run_event.run_id,
                system=start_run_event.system,
                simulation=start_run_event.simulation,
                fragments=[rf],
                inst=start_run_event.inst,
                produced_at=start_run_event.produced_at,
                id=start_run_event.id,
            )

            # set instantiation specific artifact
            if inst_artifact is not None:
                start_fragment_event[runner_utils.START_RUN_ADD_INST_ART] = base64.b64encode(
                    inst_artifact
                ).decode("utf-8")

            # set fragment specific artifact
            assert rf.fragment_id in fragment_map
            fragment = fragment_map[rf.fragment_id]
            inst_fragment = sb_inst.get_fragment(fragment.object_id)
            if inst_fragment.input_artifact_paths:
                fragment_artifact = await self._simbricks_client.get_fragment_input_artifact_raw(
                    start_run_event.inst.id, rf.fragment_id
                )
                start_fragment_event[runner_utils.START_RUN_ADD_FRAG_ART] = base64.b64encode(
                    fragment_artifact
                ).decode("utf-8")

            senders.append(
                asyncio.create_task(
                    fragment_runner_map[rf.id].fragment_runner.send_events([start_fragment_event])
                )
            )

        try:
            await asyncio.gather(*senders)
        except asyncio.CancelledError:
            for sender in senders:
                sender.cancel()
                try:
                    await sender
                except asyncio.CancelledError:
                    pass
            raise

        # TODO: should we wait here until all fragment executors sent their successful update
        # events? Only then we have also already updated the state of the StartRunEvent in the
        # backend and do not accidentally fetch the same StartRunEvent again.

    async def _handel_events(self) -> None:

        while True:

            for run_id in list(self._run_map.keys()):
                run = self._run_map[run_id]
                for fragment_state in run.fragment_run_state.values():
                    if fragment_state in [RunState.SPAWNED, RunState.PENDING, RunState.RUNNING]:
                        break
                else:
                    await self._stop_fragment_runners(run.fragment_runner_map)
                    self._run_map.pop(run_id)
                    LOGGER.debug(f"removed run {run_id} from run_map")

            cursor_next: str | None = None
            # fetch all events not handled yet
            fetched_events_bundle = await self._rc.retrieve_events(cursor_next=cursor_next)

            # remember the cursor of already fetched events
            links = fetched_events_bundle.links
            if isinstance(links, PaginationLinks):
                next_links = links.next_
                if isinstance(next_links, str):
                    cursor_next = next_links

            LOGGER.debug(f"events fetched ({len(fetched_events_bundle.data)})")

            for event in fetched_events_bundle.data:
                match event:
                    case RunnerHeartbeatReq():
                        heartbeat = RunnerHeartbeat()
                        await self._rc.submit_event(heartbeat)
                        LOGGER.debug(f"heartbeat sent")

                    case StartRunReq():
                        if event.run_id in self._run_map:
                            LOGGER.info(
                                f"cannot start run, run with id {event.run_id} is already being executed"
                            )
                            continue

                        try:
                            await self._start_run(event)
                            LOGGER.debug(f"started execution of run {event.run_id}")
                        except Exception:
                            trace = traceback.format_exc()
                            LOGGER.error(f"could not start run {event.run_id}: {trace}")
                            run_error = RunStatus(run_id=event.run_id, run_state=RunState.ERROR)
                            await self._rc.submit_event(run_error)

                    case (
                        KillRunReq()
                        | SimulationSigusr1()
                        | SimulatorChangedState()
                        | ProxyChangedState()
                    ):
                        if event.run_id not in self._run_map:
                            LOGGER.info(
                                f"Cannot send kill /sigusr1 / simulator state change to run {event.run_id} as not in run map"
                            )
                            continue

                        await self._send_events_aggregate_updates(event)
                        LOGGER.debug("send passthrough event to all fragment runners")

                    case _:
                        LOGGER.error(
                            f"encountered not yet handled event type: {event} {type(event)}"
                        )

            if cursor_next is not None:
                await self._rc.delete_retrieved_events_until_event(cursor_next)

            await asyncio.sleep(self._polling_delay_sec)

    async def _handle_fragment_runner_events(self):
        while True:
            frag_runner_event = await self.fragment_runner_events.get()

            for event in frag_runner_event.events:
                match event:
                    case (
                        SimulatorOutput()
                        | SimulatorStateChange()
                        | ProxyStateChange()
                        | ProxyOutput()
                        | FragmentOutputArtifact()
                    ):
                        pass
                    case FragmentStateChange():
                        run = self._run_map[event.run_id]
                        run.fragment_run_state[event.run_fragment_id] = event.run_state
                    case _:
                        raise Exception(
                            f"_handle_fragment_runner_events unkown event type: {event}"
                        )

            await self._rc.submit_events(frag_runner_event.events)

    # TODO: abort a run if the fragment executor fails/the connection breaks
    async def _read_fragment_runner_events(self, fragment_runner: FragmentRunner):
        try:
            while True:
                events = await fragment_runner.fragment_runner.get_events()
                await self.fragment_runner_events.put(FragmentRunnerEvent(fragment_runner, events))
        except Exception:
            LOGGER.error(
                f"failed to read events from runner {fragment_runner.fragment_runner.name()}"
            )
            raise

    def _load_configuration(self, configuration_file: str) -> None:
        # load yaml configuration
        configuration = None
        with open(configuration_file, "r", encoding="utf-8") as cf:
            configuration = yaml.load(cf, yaml.FullLoader)
        assert configuration is not None

        if not isinstance(configuration, dict) or "fragment_executors" not in configuration:
            raise RuntimeError("invalid configuration format")

        executors = configuration["fragment_executors"]
        if not isinstance(executors, list):
            raise RuntimeError("invalid configuration format")

        loaded_plugins: dict[str, type[plugin.FragmentRunnerPlugin]] = {}

        for executor in executors:
            if not isinstance(executor, dict) or len(executor) != 1:
                raise RuntimeError("invalid configuration format")

            executor_name = list(executor.keys())[0]
            executor_data = executor[executor_name]

            if not isinstance(executor_data, dict) or "plugin" not in executor_data:
                raise RuntimeError("invalid configuration format")

            plugin = executor_data["plugin"]

            settings: dict[tp.Any, tp.Any] = {}
            if "settings" in executor_data:
                if not isinstance(executor_data["settings"], dict):
                    raise RuntimeError("invalid configuration format")
                settings = executor_data["settings"]

            if plugin not in loaded_plugins:
                loaded_plugin = plugin_loader.load_plugin(plugin)
                loaded_plugins[plugin] = loaded_plugin

            fragment_executor = FragmentExecutorConfiguration(
                executor_name, loaded_plugins[plugin], settings
            )

            if executor_name in self._fragment_executor_configs:
                raise KeyError(f"fragment executor configuration {executor_name} already exists")

            self._fragment_executor_configs[executor_name] = fragment_executor
            self._available_fragment_executors.append(executor_name)

        for fragment_executor in self._available_fragment_executors:
            self.fragment_runners[fragment_executor] = set()

    async def run(self, configuration_file: str):
        workers: list[asyncio.Task] = []
        try:
            self._load_configuration(configuration_file)

            if not self._available_fragment_executors:
                raise RuntimeError("no fragment executor configurations loaded")

            LOGGER.debug("notify backend that runner has started")
            plugin_tags = [RunnerTag(label=p) for p in self._available_fragment_executors]
            started_event = RunnerStarted(plugin_tags=plugin_tags)
            await self._rc.submit_event(started_event)

            LOGGER.debug("start worker tasks")
            workers.append(asyncio.create_task(self._handle_fragment_runner_events()))
            workers.append(asyncio.create_task(self._handel_events()))
            await asyncio.gather(*workers)
        except (asyncio.CancelledError, Exception):
            LOGGER.warning("aborting run loop and cleaning up")
            for worker in workers:
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    LOGGER.debug(f"cancelled worker task {worker.get_name()}")
            for executor in itertools.chain(*self.fragment_runners.values()):
                await asyncio.shield(executor.stop())
            raise


async def amain():
    base_url=settings.runner_settings().base_url
    namespace=settings.runner_settings().namespace
    ident=settings.runner_settings().runner_id

    settings.runner_settings().telemetry.service_name = f"simb-runner-{ident}"
    setup_telemetry(settings.runner_settings().telemetry)

    nsc = await client.ns_client(base_url, namespace)
    sbc = await client.simb_client(nsc)
    ruc = await client.runner_client(ident, nsc)

    runner = MainRunner(
        nsc,
        ruc,
        sbc,
        ident,
        polling_delay_sec=settings.runner_settings().polling_delay_sec,
    )

    if settings.runner_settings().configuration_file == "":
        raise RuntimeError("no configuration file given")

    await runner.run(settings.runner_settings().configuration_file)


def setup_logger() -> logging.Logger:
    level = settings.RunnerSettings().log_level
    logging.basicConfig(
        level=level,
        format="%(asctime)s - runner - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logging.getLogger("httpx").disabled = True
    return logger


LOGGER = setup_logger()


def main():
    try:
        LOGGER.info("Hello, starting the runner...")
        asyncio.run(amain())
    except KeyboardInterrupt:
        LOGGER.info("received keyboard interrupt, shutting down...")
        LOGGER.info("Bye!")
    except:
        trace = traceback.format_exc()
        LOGGER.error(f"Fatal error:\n{trace}")
        exit(1)


if __name__ == "__main__":
    main()
