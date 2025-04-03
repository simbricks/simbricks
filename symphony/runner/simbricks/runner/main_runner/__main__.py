from __future__ import annotations

import abc
import asyncio
import logging
import traceback

from simbricks import client
from simbricks.runner.main_runner import settings
from simbricks.runner.main_runner.plugins import plugin
from simbricks.runner.main_runner.plugins import plugin_loader
from simbricks.schemas import base as schemas
from simbricks.utils import base as utils_base
from simbricks.utils import load_mod


class MainRun:
    def __init__(
        self,
        run_id: int,
        #inst: inst_base.Instantiation,
        fragment_runner_map: dict[int, FragmentRunner],
    ) -> None:
        self.run_id = run_id
        self.fragment_runner_map = fragment_runner_map
        #self.inst: inst_base.Instantiation = inst
        self.cancelled: bool = False
        self.fragment_run_state: dict[int, schemas.RunState] = {}
        for fragment in fragment_runner_map:
            self.fragment_run_state[fragment] = schemas.RunState.SPAWNED
        self.run_state_callback: EventCallback | None = None


class EventCallback(abc.ABC):

    def __init__(self, handlers: list[dict[str, set[EventCallback]]], event_type: str):
        self.handlers = handlers
        self.event_type = event_type
        for handler in self.handlers:
            hs = handler.setdefault(self.event_type, set())
            hs.add(self)

    def remove_callback(self):
        for handler in self.handlers:
            handler[self.event_type].remove(self)

    @abc.abstractmethod
    async def callback(self, event) -> bool:
        pass

    @abc.abstractmethod
    def passthrough(self) -> bool:
        pass


class BundleUpdatesEventCallback(EventCallback):

    def __init__(
            self,
            handlers,
            event_type,
            event_id: int,
            runners: int,
            update_event: schemas.ApiEventUpdate_U,
            rc: client.RunnerClient
    ):
        super().__init__(handlers, event_type)
        self.event_id = event_id
        self.runners = runners
        self.received_updates = 0
        self.success = True
        self.update_event = update_event
        self.rc = rc

    async def callback(self, event: schemas.ApiEventUpdate_U):
        if self.event_id != event.id:
            return False
        assert self.received_updates < self.runners
        self.received_updates += 1
        if event.event_status != schemas.ApiEventStatus.COMPLETED:
            self.success = False

        if self.received_updates == self.runners:
            event_bundle = schemas.ApiEventBundle()
            if self.success:
                self.update_event.event_status = schemas.ApiEventStatus.COMPLETED
            else:
                self.update_event.event_status = schemas.ApiEventStatus.ERROR
            event_bundle.add_event(self.update_event)
            await self.rc.update_events(event_bundle)
            self.remove_callback()
        return True

    def passthrough(self):
        return False


class RunFragmentStateCallback(EventCallback):

    def __init__(self, handlers, event_type, run: MainRun):
        super().__init__(handlers, event_type)
        self.run = run

    async def callback(self, event: schemas.ApiEventCreate_U) -> bool:
        assert isinstance(event, schemas.ApiRunFragmentStateEventCreate)
        if event.run_id != self.run.run_id:
            return False
        self.run.fragment_run_state[event.fragment_id] = event.run_state
        return True

    def passthrough(self) -> bool:
        return True

class FragmentRunner:
    def __init__(self, fragment_runner: plugin.FragmentRunnerPlugin):
        self.fragment_runner = fragment_runner
        self.read_task: asyncio.Task | None = None
        self.create_event_handlers: dict[str, set[EventCallback]] = {}
        self.update_event_handlers: dict[str, set[EventCallback]] = {}
        self.delete_event_handlers: dict[str, set[EventCallback]] = {}
        self.query_event_handlers: dict[str, set[EventCallback]] = {}

    async def stop(self):
        self.create_event_handlers.clear()
        self.update_event_handlers.clear()
        self.delete_event_handlers.clear()
        self.query_event_handlers.clear()
        self.read_task.cancel()
        await self.fragment_runner.stop()


class FragmentRunnerEvent:
    def __init__(
            self, fragment_runner: FragmentRunner,
            event_type: schemas.ApiEventType,
            event_bundle: schemas.ApiEventBundle,
    ):
        self.fragment_runner = fragment_runner
        self.event_type = event_type
        self.event_bundle = event_bundle


class MainRunner:

    def __init__(
            self,
            base_url: str,
            namespace: str,
            ident: int,
            polling_delay_sec: int,
            plugin_paths: list[str]
    ):
        self._ident = ident
        self._polling_delay_sec = polling_delay_sec

        self.loaded_plugins: dict[str, type[plugin.FragmentRunnerPlugin]] = {}
        self.fragment_runners: dict[str, set[FragmentRunner]] = {}
        self.fragment_runner_events = asyncio.Queue[FragmentRunnerEvent]()

        self._base_client = client.BaseClient(base_url=base_url)
        self._namespace_client = client.NSClient(base_client=self._base_client, namespace=namespace)
        self._rc = client.RunnerClient(self._namespace_client, ident)

        self._run_map: dict[int, MainRun] = {}

        try:
            self.loaded_plugins = plugin_loader.load_plugins(plugin_paths)
        except (plugin_loader.RunnerPluginLoadError, load_mod.SimBricksModuleLoadError) as err:
            print(f"Error occured during loading of runner plugins:\n{err}")
            exit(1)

        for plugin in self.loaded_plugins:
            self.fragment_runners[plugin] = set()

    async def _send_events_aggregate_updates(
        self, run_id: int, event, event_type: str, update
    ) -> None:
        run = self._run_map[run_id]

        # add handlers for update events from fragment runners
        handlers = []
        for runner in run.fragment_runner_map.values():
            handlers.append(runner.update_event_handlers)
        BundleUpdatesEventCallback(
            handlers, event_type, event.id, len(run.fragment_runner_map), update, self._rc
        )

        # send event to fragment runners
        event_bundle = schemas.ApiEventBundle()
        event_bundle.add_event(event)
        senders = []
        for runner in run.fragment_runner_map.values():
            senders.append(asyncio.create_task(
                runner.fragment_runner.send_events(
                    event_bundle, schemas.ApiEventType.ApiEventRead
                )
            ))

        await asyncio.gather(*senders)

    async def _stop_ephemeral_fragment_runners(
            self, fragment_runner_map: dict[int, FragmentRunner]
    ):
        stop = []
        for runner in fragment_runner_map.values():
            if runner.fragment_runner.ephemeral():
                stop.append(asyncio.create_task(runner.stop()))
                self.fragment_runners[runner.fragment_runner.name()].remove(runner)

        await asyncio.gather(*stop)

    async def _start_run(self, run_id: int, event: schemas.ApiRunEventStartRunRead, update):
        fragment_runner_map: dict[int, FragmentRunner] = {}
        for id, name in event.fragments:
            if name not in self.loaded_plugins:
                await self._stop_ephemeral_fragment_runners(fragment_runner_map)
                raise RuntimeError(f"unsupported fragment runner type {name}")
            if (self.loaded_plugins[name].ephemeral() or not self.fragment_runners[name]):
                runner = self.loaded_plugins[name]()
                await runner.start()
                read_task = asyncio.create_task(self._read_fragment_runner_events(runner))
                fragment_runner = FragmentRunner(runner, read_task)
                fragment_runner_map[id] = fragment_runner
                self.fragment_runners[name].add(fragment_runner)
            else:
                assert len(self.fragment_runners[name]) == 1
                fragment_runner_map[id] = list(self.fragment_runners[name])[0]

        run = MainRun(run_id, fragment_runner_map)
        self._run_map[run_id] = run

        handlers = []
        for runner in fragment_runner_map.values():
            handlers.append(runner.update_event_handlers)
        BundleUpdatesEventCallback(
            handlers, "ApiRunEventUpdate", event.id, len(run.fragment_runner_map), update, self._rc
        )

        handlers = []
        for runner in fragment_runner_map.values():
            handlers.append(runner.create_event_handlers)
        callback = RunFragmentStateCallback(handlers, "ApiRunFragmentStateEventCreate", run)
        run.run_state_callback = callback

        senders = []
        for fragment_id, name in event.fragments:
            fragment_event = event.model_copy()
            fragment_event.fragments = [(fragment_id, name)]
            event_bundle = schemas.ApiEventBundle()
            event_bundle.add_event(fragment_event)
            senders.append(asyncio.create_task(
                fragment_runner_map[fragment_id].fragment_runner.send_events(
                    event_bundle, schemas.ApiEventType.ApiEventRead
                )
            ))

        await asyncio.gather(*senders)

    async def _handle_run_events(
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
            assert run_id is not None
            match event.run_event_type:
                case schemas.RunEventType.KILL:
                    if run_id not in self._run_map:
                        update.event_status = schemas.ApiEventStatus.CANCELLED
                        updates.add_event(update)
                    else:
                        await self._send_events_aggregate_updates(
                            run_id, event, "ApiRunEventUpdate", update
                        )
                        LOGGER.debug(
                            "send kill event to fragment runners to "
                            f"cancel execution of run {run_id}"
                        )
                case schemas.RunEventType.SIMULATION_STATUS:
                    if run_id not in self._run_map:
                        update.event_status = schemas.ApiEventStatus.CANCELLED
                        updates.add_event(update)
                    else:
                        await self._send_events_aggregate_updates(
                            run_id, event, "ApiRunEventUpdate", update
                        )
                        LOGGER.debug(
                            f"send simulation status events to fragment runners of run {run_id}"
                        )
                case schemas.RunEventType.START_RUN:
                    assert event.event_discriminator == "ApiRunEventStartRunRead"
                    event = schemas.ApiRunEventStartRunRead.model_validate(event)
                    if run_id in self._run_map:
                        LOGGER.debug(
                            f"cannot start run, run with id {run_id} is already being executed"
                        )
                        update.event_status = schemas.ApiEventStatus.CANCELLED
                        updates.add_event(update)
                    else:
                        try:
                            await self._start_run(run_id, event, update)
                            LOGGER.debug(f"started execution of run {run_id}")
                        except Exception:
                            trace = traceback.format_exc()
                            LOGGER.error(f"could not start run {run_id}: {trace}")
                            await self._rc.update_run(run_id, schemas.RunState.ERROR, "")
                            update.event_status = schemas.ApiEventStatus.ERROR
                            updates.add_event(update)

            LOGGER.info(f"handled run related event {event.id}")

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

    async def _handel_events(self) -> None:
        try:
            await self._rc.runner_started([])

            while True:
                # fetch all events not handled yet
                event_query_bundle = schemas.ApiEventBundle[schemas.ApiEventQuery_U]()

                # query events for the runner itself that do not relate to a specific run
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

                for run_id in list(self._run_map.keys()):
                    run = self._run_map[run_id]
                    for fragment_state in run.fragment_run_state.values():
                        if fragment_state < schemas.RunState.COMPLETED:
                            break
                    else:
                        if run.run_state_callback is not None:
                            run.run_state_callback.remove_callback()
                        await self._stop_ephemeral_fragment_runners(run.fragment_runner_map)
                        self._run_map.pop(run_id)
                        LOGGER.debug(f"removed run {run_id} from run_map")

                fetched_events_bundle = await self._rc.fetch_events(event_query_bundle)

                LOGGER.debug(
                    f"events fetched ({len(fetched_events_bundle.events)}): {fetched_events_bundle.events}"
                )

                update_events_bundle = schemas.ApiEventBundle[schemas.ApiEventUpdate_U]()
                for key in fetched_events_bundle.events.keys():
                    events = fetched_events_bundle.events[key]
                    match key:
                        # handle events that are just related to the runner itself, independent of any runs
                        case "ApiRunnerEventRead":
                            await self._handle_runner_events(events, update_events_bundle)
                        # handle events related to a run that is currently being executed
                        case ("ApiRunEventStartRunRead" | "ApiRunEventRead"):
                            await self._handle_run_events(events, update_events_bundle)
                        case _:
                            LOGGER.error(f"encountered not yet handled event type {key}")

                if not update_events_bundle.empty():
                    await self._rc.update_events(update_events_bundle)

                await asyncio.sleep(self._polling_delay_sec)

        except asyncio.CancelledError as err:
            LOGGER.error(f"cancelled event handling loop")
            raise err

        except Exception:
            trace = traceback.format_exc()
            LOGGER.error(f"an error occured while running: {trace}")

    async def _apply_callbacks(self, event_bundle: schemas.ApiEventBundle, callbacks: dict[str, set[EventCallback]]) -> schemas.ApiEventBundle:
        passthrough_events = schemas.ApiEventBundle()
        for event_type, events in event_bundle.events.items():
            if event_type not in callbacks:
                passthrough_events.add_events(*events)
                continue
            for event in events:
                for callback in callbacks[event_type]:
                    if await callback.callback(event):
                        if callback.passthrough():
                            passthrough_events.add_event(event)
                        break
                else:
                    passthrough_events.add_event(event)
        return passthrough_events

    async def _handle_fragment_runner_events(self):
        while True:
            event = await self.fragment_runner_events.get()
            read_events = None
            match event.event_type:
                case schemas.ApiEventType.ApiEventCreate:
                    passthrough_events = await self._apply_callbacks(event.event_bundle, event.fragment_runner.create_event_handlers)
                    if not passthrough_events.empty():
                        read_events = await self._rc.create_events(passthrough_events)
                case schemas.ApiEventType.ApiEventUpdate:
                    passthrough_events = await self._apply_callbacks(event.event_bundle, event.fragment_runner.update_event_handlers)
                    if not passthrough_events.empty():
                        read_events = await self._rc.update_events(passthrough_events)
                case schemas.ApiEventType.ApiEventDelete:
                    passthrough_events = await self._apply_callbacks(event.event_bundle, event.fragment_runner.delete_event_handlers)
                    if not passthrough_events.empty():
                        await self._rc.delete_events(passthrough_events)
                case schemas.ApiEventType.ApiEventQuery:
                    passthrough_events = await self._apply_callbacks(event.event_bundle, event.fragment_runner.query_event_handlers)
                    if not passthrough_events.empty():
                        read_events = await self._rc.fetch_events(passthrough_events)
                case schemas.ApiEventType.ApiEventRead:
                    raise RuntimeError("we should not receive read events from fragment runners")

            if read_events is not None and not read_events.empty():
                await event.fragment_runner.fragment_runner.send_events(read_events, schemas.ApiEventType.ApiEventRead)

    async def _read_fragment_runner_events(self, fragment_runner: FragmentRunner):
        while True:
            (event_type, events) = await fragment_runner.fragment_runner.get_events()
            await self.fragment_runner_events.put(
                FragmentRunnerEvent(fragment_runner, event_type, events)
            )

    async def run(self):
        # start non-ephemeral plugins
        for name, plugin in self.loaded_plugins.items():
            if not plugin.ephemeral():
                runner = plugin()
                await runner.start()
                fragment_runner = FragmentRunner(runner)
                fragment_runner.read_task = asyncio.create_task(
                    self._read_fragment_runner_events(fragment_runner)
                )
                self.fragment_runners[name].add(fragment_runner)

        plugin_tags = [schemas.ApiRunnerTag(label=p) for p in self.loaded_plugins]
        await self._rc.runner_started(plugin_tags)

        workers = []
        workers.append(asyncio.create_task(self._handle_fragment_runner_events()))
        workers.append(asyncio.create_task(self._handel_events()))
        await asyncio.gather(*workers)

    async def cleanup(self):
        for _, runners in self.fragment_runners.items():
            for runner in runners:
                await runner.stop()


async def amain(paths):
    runner = MainRunner(
        base_url=settings.runner_settings().base_url,
        namespace=settings.runner_settings().namespace,
        ident=settings.runner_settings().runner_id,
        polling_delay_sec=settings.runner_settings().polling_delay_sec,
        plugin_paths=paths,
    )

    try:
        await runner.run()
    except Exception as err:
        print(f"Fatal error: {err}")
        await runner.cleanup()
        exit(1)
    await runner.cleanup()


def setup_logger() -> logging.Logger:
    level = settings.RunnerSettings().log_level
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger(__name__)
    return logger


LOGGER = setup_logger()


def main():
    asyncio.run(amain(["/workspaces/simbricks/symphony/runner/simbricks/runner/main_runner/plugins/local_plugin.py"]))


if __name__ == "__main__":
    main()