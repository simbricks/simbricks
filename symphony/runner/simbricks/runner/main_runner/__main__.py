import asyncio
import logging

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
        fragment_runner_map: dict[int, plugin.FragmentRunnerPlugin],
    ) -> None:
        self.run_id = run_id
        self.fragment_runner_map = fragment_runner_map
        #self.inst: inst_base.Instantiation = inst
        self.cancelled: bool = False


class MainRunner:

    def __init__(
            self,
            base_url: str,
            workdir: str,
            namespace: str,
            ident: int,
            polling_delay_sec: int,
            plugin_paths: list[str]
        ):
        self._ident = ident
        self._polling_delay_sec = polling_delay_sec

        self.loaded_plugins: dict[str, plugin.FragmentRunnerPlugin] = {}
        self.fragment_runners: dict[str, list[plugin.FragmentRunnerPlugin]] = {}

        self._base_client = client.BaseClient(base_url=base_url)
        self._namespace_client = client.NSClient(base_client=self._base_client, namespace=namespace)
        self._rc = client.RunnerClient(self._namespace_client, ident)

        self._run_map: dict[int, MainRun] = {}

        try:
            self.loaded_plugins = plugin_loader.load_plugins(plugin_paths)
        except (plugin_loader.RunnerPluginLoadError, load_mod.SimBricksModuleLoadError) as err:
            print(f"Error occured during loading of runner plugins:\n{err}")
            exit(1)

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
                    else:
                        run = self._run_map[run_id]
                        # TODO: send kill event to all of the fragment runners that are used for
                        # this run, then wait for all the update events of the fragment runners that
                        # tell us that they completed the kill, afterwards send the update with
                        # status completed back to the backend
                        run.exec_task.cancel()
                        await run.exec_task
                        update.event_status = schemas.ApiEventStatus.COMPLETED
                        LOGGER.debug(f"executed kill to cancel execution of run {run_id}")
                case schemas.RunEventType.SIMULATION_STATUS:
                    if run_id not in self._run_map:
                        update.event_status = schemas.ApiEventStatus.CANCELLED
                    else:
                        run = self._run_map[run_id]
                        # TODO: do the same as for the kill event
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
                        # TODO: need to do the assignment of fragments to fragment runners here and
                        # start fragment runner if needed, probably better to do this in a separate
                        # function
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

                # TODO: move these queries to the fragment runners
                # if self._run_map:
                #     # query events indicating that proxies are now ready
                #     state_change_q = schemas.ApiProxyStateChangeEventQuery(
                #         run_ids=list(self._run_map.keys()),
                #         proy_states=[schemas.RunComponentState.RUNNING],
                #     )
                #     event_query_bundle.add_event(state_change_q)

                #     for id, run in self._run_map.items():
                #         simulator_term_q = schemas.ApiSimulatorStateChangeEventQuery(
                #             run_ids=[id],
                #             simulator_ids=list(run.runner._wait_sims.keys()),
                #             simulator_states=[schemas.RunComponentState.TERMINATED],
                #         )
                #         event_query_bundle.add_event(simulator_term_q)

                # TODO: I need to check whether all fragment runners have finished
                # for run_id in list(self._run_map.keys()):
                #     run = self._run_map[run_id]
                #     # check if run finished and cleanup map
                #     if run.exec_task and run.exec_task.done():
                #         run = self._run_map.pop(run_id)
                #         LOGGER.debug(f"removed run {run_id} from run_map")
                #         assert run_id not in self._run_map
                #         continue

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

        except asyncio.CancelledError:
            LOGGER.error(f"cancelled event handling loop")
            await self._cancel_all_tasks()

        except Exception:
            await self._cancel_all_tasks()
            trace = traceback.format_exc()
            LOGGER.error(f"an error occured while running: {trace}")

    async def _read_fragment_runner_events(self, plugin: plugin.FragmentRunnerPlugin):
        while True:
            (event_type, events) = await plugin.get_events()
            read_events = None
            match event_type:
                case schemas.ApiEventType.ApiEventCreate:
                    read_events = await self._rc.create_events(events)
                case schemas.ApiEventType.ApiEventUpdate:
                    read_events = await self._rc.update_events(events)
                case schemas.ApiEventType.ApiEventDelete:
                    await self._rc.delete_events(events)
                case schemas.ApiEventType.ApiEventQuery:
                    read_events = await self._rc.fetch_events(events)
                case schemas.ApiEventType.ApiEventRead:
                    raise RuntimeError("we should not receive read events from fragment runners")

            if read_events is not None and not read_events.empty():
                await plugin.send_events(read_events, schemas.ApiEventType.ApiEventRead)

    async def test_env(self):
        plugin = list(self.loaded_plugins.values())[0]()
        await plugin.start()
        while "forever":
            length_str = await plugin.read(12)
            print(f"length_str: {length_str}")
            if length_str == "":
                raise RuntimeError("connection broken")
            length = int(length_str, 16)
            data = await plugin.read(length)
            if data == "":
                raise RuntimeError("connection broken")
            print("------new event------")
            print(f"length: {hex(length)}, {length}")
            print(f"data: {data}")
            

    async def run(self):
        # start non-ephemeral plugins
        for name, plugin in self.loaded_plugins.items():
            if not plugin.ephemeral():
                p = plugin()
                if name in self.fragment_runners:
                    self.fragment_runners[name].append(p)
                else:
                    self.fragment_runners[name] = [p]
                await p.start()

        plugin_tags = [schemas.ApiRunnerTag(label=p) for p in self.loaded_plugins]
        await self._rc.runner_started(plugin_tags)

        #await self._handel_events()
        await self.test_env()

    async def cleanup(self):
        for _, runners in self.fragment_runners.items():
            for runner in runners:
                await runner.stop()


async def amain(paths):
    runner = MainRunner(paths)

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
    asyncio.run(amain(["/workspaces/simbricks/symphony/runner/simbricks/runner/main_runner/plugins/test_plugin.py"]))


if __name__ == "__main__":
    main()