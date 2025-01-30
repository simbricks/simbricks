# Copyright 2021 Max Planck Institute for Software Systems, and
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

import abc
import datetime
import enum
from typing import TypeVar, Generic, Literal, Annotated
from pydantic import BaseModel, TypeAdapter, Field


class ApiNamespace(BaseModel):
    id: int | None = None
    parent_id: int | None = None
    name: str


ApiNamespaceList_A = TypeAdapter(list[ApiNamespace])


class ApiSystem(BaseModel):
    id: int | None = None
    sb_json: str | dict | None = None
    namespace_id: int | None = None


ApiSystemList_A = TypeAdapter(list[ApiSystem])


class ApiSystemQuery(BaseModel):
    namespace_id: int | None = None
    limit: int | None = None


class ApiSimulation(BaseModel):
    id: int | None = None
    namespace_id: int = None
    system_id: int = None
    sb_json: str | dict | None = None


ApiSimulationList_A = TypeAdapter(list[ApiSimulation])


class ApiSimulationQuery(BaseModel):
    id: int | None = None
    namespace_id: int = None
    system_id: int = None
    limit: int | None = None


class ApiFragment(BaseModel):
    id: int | None = None
    instantiation_id: int | None = None
    cores_required: int | None = None
    memory_required: int | None = None


class ApiFragmentQuery(BaseModel):
    id: int | None = None
    instantiation_id: int | None = None
    limit: int | None = None


class ApiInstantiation(BaseModel):
    id: int | None = None
    simulation_id: int | None = None
    sb_json: str | dict | None = None
    fragments: list[ApiFragment] = []


ApiInstantiationList_A = TypeAdapter(list[ApiInstantiation])


class ApiInstantiationQuery(BaseModel):
    id: int | None = None
    simulation_id: int | None = None
    fragments: list[ApiFragmentQuery] = []
    limit: int | None = None


class RunState(str, enum.Enum):
    SPAWNED = "spawned"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ApiRun(BaseModel):
    id: int | None = None
    namespace_id: int | None = None
    instantiation_id: int | None = None
    state: RunState | None = None
    output: str | None = None


ApiRunList_A = TypeAdapter(list[ApiRun])


class ApiRunQuery(BaseModel):
    id: int | None = None
    namespace_id: int | None = None
    instantiation_id: int | None = None
    state: RunState | None = None
    limit: int | None = None


class ApiResourceGroup(BaseModel):
    id: int | None = None
    label: str | None = None
    namespace_id: int | None = None
    available_cores: int | None = None
    available_memory: int | None = None
    cores_left: int | None = None
    memory_left: int | None = None


ApiResourceGroupList_A = TypeAdapter(list[ApiResourceGroup])


class ApiRunnerTag(BaseModel):
    label: str


class ApiRunner(BaseModel):
    id: int | None = None
    label: str | None = None
    namespace_id: int | None = None
    resource_group_id: int | None = None
    tags: list[ApiRunnerTag] = []


ApiRunnerList_A = TypeAdapter(list[ApiRunner])


class RunnerEventAction(str, enum.Enum):
    KILL = "kill"
    HEARTBEAT = "heartbeat"
    SIMULATION_STATUS = "simulation_status"
    START_RUN = "start_run"


class RunnerEventStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ApiRunnerEvent(BaseModel):
    id: int | None = None
    action: RunnerEventAction | None = None
    run_id: int | None = None
    runner_id: int
    event_status: RunnerEventStatus | None = None


ApiRunnerEventList_A = TypeAdapter(list[ApiRunnerEvent])


class UpdateApiRunnerEvent(BaseModel):
    id: int
    action: RunnerEventAction | None = None
    run_id: int | None = None
    runner_id: int | None = None
    event_status: RunnerEventStatus | None = None


class ApiRunnerEventQuery(BaseModel):
    action: RunnerEventStatus | None = None
    run_id: int | None = None
    event_status: RunnerEventStatus | None = None
    runner_id: int | None = None
    limit: int | None = None


class RunSimulatorState(str, enum.Enum):
    UNKNOWN = "unknown"
    PREPARING = "preparing"
    STARTING = "starting"
    RUNNING = "running"
    TERMINATED = "terminated"


class ApiSimulatorState(BaseModel):
    run_id: int | None = None
    simulator_id: int | None = None
    simulator_name: str | None = None
    command: str | None = None
    state: RunSimulatorState | None = None


class ApiConsoleOutputLine(BaseModel):
    created_at: datetime.datetime
    output: str
    is_stderr: bool


class ApiRunSimulatorOutput:
    run_id: int
    simulator_id: int
    output_lines: list[ApiConsoleOutputLine] = []


class ApiRunComponent(BaseModel):
    name: str
    commands: dict[str, list[ApiConsoleOutputLine]] = {}


class ApiRunOutput(BaseModel):
    run_id: int
    simulators: dict[int, ApiRunComponent] = {}


class ApiRunOutputSeenUntil(BaseModel):
    simulators: dict[int, datetime.datetime] | None = None


class ApiOrgInvite(BaseModel):
    email: str
    first_name: str
    last_name: str


class ApiOrgGuestCred(BaseModel):
    email: str


class ApiOrgGuestMagicLinkResp(BaseModel):
    magic_link: str


"""
Schema objects used in SimBricks 'Generic Event Handling Interface':
"""


class ApiEventStatus(str, enum.Enum):
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class ApiEventType(str, enum.Enum):
    """
    NOTE: DO NOT confuse this enum with belows union of the different event types.
    """

    ApiRunnerAssocEvent = "ApiRunnerAssocEvent"
    ApiRunAssocEvent = "ApiRunAssocEvent"
    ApiSimulatorAssocEvent = "ApiSimulatorAssocEvent"
    ApiProxyAssocEvent = "ApiProxyAssocEvent"


class AbstractApiEvent(BaseModel, abc.ABC):
    id: int | None = None
    """
    Generic identifier for an event.
    """
    event_type: Literal["AbstractApiEvent"] = "AbstractApiEvent"
    """
    The event type, can be used to reconstruct pydantic model. 
    Must be OVERWRITTEN as Literal IN SUBCLASSES.
    """
    event_status: ApiEventStatus = ApiEventStatus.PENDING
    """
    The status of this specific event.
    """
    event_metadata_json: dict | str | bytes | None = None
    """
    Optional event metadata that can be stored in this blob which is 
    'independent' of the schema.
    """


class ApiRunnerAssocEvent(AbstractApiEvent):
    runner_id: int
    """
    the runner the event is associated with
    """
    event_type: Literal[ApiEventType.ApiRunnerAssocEvent] = ApiEventType.ApiRunnerAssocEvent
    """
    override
    """
    # TODO: FIXME add type etc and othe required fields...


ApiRunnerAssocEvent_List_A = TypeAdapter(list[ApiRunnerAssocEvent])


class ApiRunAssocEvent(AbstractApiEvent):
    runner_id: int
    """
    The runner the run is associated with.
    """
    run_id: int
    """
    The run associated with.
    """
    event_type: Literal[ApiEventType.ApiRunAssocEvent] = ApiEventType.ApiRunAssocEvent
    """
    override
    """
    # TODO: FIXME add type etc and othe required fields...


ApiRunAssocEvent_List_A = TypeAdapter(list[ApiRunAssocEvent])


class ApiSimulatorAssocEvent(AbstractApiEvent):
    runner_id: int
    """
    The runner a fragment is associated with.
    """
    run_id: int
    """
    The run a fragment is associated with.
    """
    simulation_id: int
    """
    The simulation associated with.
    """
    event_type: Literal[ApiEventType.ApiSimulatorAssocEvent] = ApiEventType.ApiSimulatorAssocEvent
    """
    override
    """
    # TODO: FIXME add type etc and othe required fields...


ApiSimulatorAssocEvent_List_A = TypeAdapter(list[ApiSimulatorAssocEvent])


class ApiProxyAssocEvent(AbstractApiEvent):
    runner_id: int
    """
    The runner a fragment is associated with.
    """
    run_id: int
    """
    The run a fragment is associated with.
    """
    proxy_id: int
    """
    the proxy id the event is associated with.
    """
    event_type: Literal[ApiEventType.ApiProxyAssocEvent] = ApiEventType.ApiProxyAssocEvent
    """
    override
    """
    # TODO: FIXME add type etc and othe required fields...


ApiProxyAssocEvent_List_A = TypeAdapter(list[ApiProxyAssocEvent])


ApiEventTypes = Annotated[
    ApiRunnerAssocEvent | ApiRunAssocEvent | ApiSimulatorAssocEvent | ApiProxyAssocEvent,
    Field(discriminator="event_type"),
]
"""
NOTE: DO NOT confuse this union with aboves enum.
"""


class ApiEventBundle(BaseModel):
    events: dict[ApiEventType, list[ApiEventTypes]] = {}
    """
    A dict that bundles events of different types in a dict. Each type is 
    associated with a bundle of events of that specific type.
    """

    def add_event(self, event: ApiEventTypes) -> None:
        if event.event_type not in self.events:
            self.events[event.event_type] = []
        self.events[event.event_type].append(event)

    def add_events(self, events: list[ApiEventTypes]):
        for event in events:
            self.add_event(event)


class ApiEventQuery(BaseModel):
    id: int | None = None
    runner_id: int | None = None
    run_id: int | None = None
    simulation_id: int | None = None
    proxy_id: int | None = None
    event_status: set[ApiEventStatus] | None = None
    event_types: set[ApiEventType] | None = None


if __name__ == "__main__":
    bundle = ApiEventBundle()
    bundle.add_event(ApiRunnerAssocEvent(runner_id=1))
    bundle.add_event(ApiRunnerAssocEvent(runner_id=2))
    bundle.add_event(ApiRunAssocEvent(runner_id=1, run_id=3))
    bundle.add_event(ApiSimulatorAssocEvent(runner_id=1, run_id=2, fragment_id=1, simulation_id=33))

    json = bundle.model_dump()
    print(json)

    deserialized = ApiEventBundle.model_validate(json)
    for type_lit, mod_list in deserialized.events.items():
        match type_lit:
            case ApiEventType.ApiRunAssocEvent:
                print(mod_list)
            case _:
                continue
