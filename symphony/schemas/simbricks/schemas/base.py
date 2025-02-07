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

from __future__ import annotations

import abc
import datetime
import enum
from typing import TypeVar, Generic, Literal, Annotated, get_args, get_origin
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


class ApiRunnerEvent(BaseModel):
    id: int | None = None
    action: RunnerEventAction | None = None
    run_id: int | None = None
    runner_id: int
    event_status: ApiEventStatus | None = None


ApiRunnerEventList_A = TypeAdapter(list[ApiRunnerEvent])


class UpdateApiRunnerEvent(BaseModel):
    id: int
    action: RunnerEventAction | None = None
    run_id: int | None = None
    runner_id: int | None = None
    event_status: ApiEventStatus | None = None


class ApiRunnerEventQuery(BaseModel):
    action: ApiEventStatus | None = None
    run_id: int | None = None
    event_status: ApiEventStatus | None = None
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


""" ############################################################################
Schema objects used in SimBricks 'Generic Event Handling Interface':
"""  ############################################################################


class ApiEventStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class AbstractApiEvent(BaseModel, abc.ABC):
    id: int
    """
    Generic identifier for an event. Subclasses should OVEWRITE this explicitly IN CASE the id is OPTIONAL.
    """
    event_discriminator: Literal["AbstractApiEvent"] = "AbstractApiEvent"
    """
    The event event_discriminator, is be used to reconstruct pydantic model. 
    Must be OVERWRITTEN as Literal IN SUBCLASSES (see belows additional helper classes).
    """
    event_status: ApiEventStatus = ApiEventStatus.PENDING
    """
    The status of this specific event.
    """
    event_metadata_json: dict | str | bytes | None = (
        None  # TODO: probably should make this a field with limited size
    )
    """
    Optional event metadata that can be stored in this blob which is 
    'independent' of the schema.
    """


class ApiCreateEvent(AbstractApiEvent, abc.ABC):
    id: None = None
    """
    overrides
    """


class ApiReadEvent(AbstractApiEvent, abc.ABC):
    pass


class ApiUpdateEvent(AbstractApiEvent, abc.ABC):
    pass


class ApiDeleteEvent(AbstractApiEvent, abc.ABC):
    pass


class AbstractApiEventQuery(abc.ABC, BaseModel):
    event_discriminator: Literal["AbstractApiEventQuery"] = "AbstractApiEventQuery"
    """
    The event event_discriminator, is be used to reconstruct pydantic model. 
    Must be OVERWRITTEN as Literal IN SUBCLASSES (see belows additional helper classes).
    """
    limit: int | None = None
    """
    Limit the results size.
    """
    ids: list[int] | None = None
    """
    Allows to query for specific event ids.
    """
    event_status: list[ApiEventStatus] | None = None
    """
    Allows to query for events with specific status.
    """


""" ############################################################################
Runner related events
"""  ############################################################################


class RunnerEventType(str, enum.Enum):
    heartbeat = "heartbeat"


class AbstractApiRunnerEvent(AbstractApiEvent, abc.ABC):
    runner_id: int
    """
    the runner the event is associated with
    """
    runner_event_type: RunnerEventType = RunnerEventType.heartbeat
    """
    The kind of runner specific event this is (e.g. heartbeat).  
    """


class ApiRunnerEventCreate(ApiCreateEvent, AbstractApiRunnerEvent):
    event_discriminator: Literal["ApiRunnerEventCreate"] = "ApiRunnerEventCreate"


class ApiRunnerEventRead(ApiReadEvent, AbstractApiRunnerEvent):
    event_discriminator: Literal["ApiRunnerEventRead"] = "ApiRunnerEventRead"


class ApiRunnerEventUpdate(ApiUpdateEvent, AbstractApiRunnerEvent):
    event_discriminator: Literal["ApiRunnerEventUpdate"] = "ApiRunnerEventUpdate"


class ApiRunnerEventDelete(ApiDeleteEvent):
    event_discriminator: Literal["ApiRunnerEventDelete"] = "ApiRunnerEventDelete"


class ApiRunnerEventQuery(AbstractApiEventQuery):
    event_discriminator: Literal["ApiRunnerEventQuery"] = "ApiRunnerEventQuery"
    runner_ids: list[int] | None = None
    runner_event_type: list[RunnerEventType] | None = None


""" ############################################################################
Run related events
"""  ############################################################################


class RunEventType(str, enum.Enum):
    kill = "kill"
    simulation_status = "simulation_status"
    start_run = "start_run"


class AbstracApiRunEvent(AbstractApiEvent, abc.ABC):
    runner_id: int
    """
    The runner the run is associated with.
    """
    run_id: int
    """
    The run associated with.
    """
    run_event_type: RunEventType
    """
    The kind of runner specific event this is (e.g. heartbeat).  
    """


class ApiRunEventCreate(ApiCreateEvent, AbstracApiRunEvent):
    event_discriminator: Literal["ApiRunEventCreate"] = "ApiRunEventCreate"


class ApiRunEventRead(ApiReadEvent, AbstracApiRunEvent):
    event_discriminator: Literal["ApiRunEventRead"] = "ApiRunEventRead"


class ApiRunEventUpdate(ApiUpdateEvent, AbstracApiRunEvent):
    event_discriminator: Literal["ApiRunEventUpdate"] = "ApiRunEventUpdate"


class ApiRunEventDelete(ApiDeleteEvent):
    event_discriminator: Literal["ApiRunEventDelete"] = "ApiRunEventDelete"


class ApiRunEventQuery(AbstractApiEventQuery):
    event_discriminator: Literal["ApiRunEventQuery"] = "ApiRunEventQuery"
    runner_ids: list[int] | None = None
    run_ids: list[int] | None = None
    run_event_type: list[RunEventType] | None = None


""" ############################################################################
Simulator related events
"""  ############################################################################


class AbstractApiSimulatorEvent(AbstractApiEvent, abc.ABC):
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
    simulator_id: int
    """
    The runtime simulators id the event is associated with.
    """


class AbstractApiOutputEvent(AbstractApiSimulatorEvent, abc.ABC):
    output_generated_at: datetime.datetime = datetime.datetime.now()
    """
    An indicator when the output was generated.
    """
    output: str
    """
    The actual output from the simulator process.
    """
    is_stderr: bool
    """
    Whether the output is from stdout or from stderr.
    """


class ApiSimulatorOutputEventCreate(ApiCreateEvent, AbstractApiOutputEvent):
    event_discriminator: Literal["ApiSimulatorOutputEventCreate"] = "ApiSimulatorOutputEventCreate"


class ApiSimulatorOutputEventRead(ApiReadEvent, AbstractApiOutputEvent):
    event_discriminator: Literal["ApiSimulatorOutputEventRead"] = "ApiSimulatorOutputEventRead"


class ApiSimulatorOutputEventDelete(ApiDeleteEvent):
    event_discriminator: Literal["ApiSimulatorOutputEventDelete"] = "ApiSimulatorOutputEventDelete"


"""
Proxy related events
"""


class AbstractApiProxyEvent(AbstractApiEvent, abc.ABC):
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


"""
ApiEventBundle definitions.
"""

ApiEventCreate_U = Annotated[
    ApiRunnerEventCreate | ApiRunEventCreate | ApiSimulatorOutputEventCreate,
    Field(discriminator="event_discriminator"),
]

ApiEventRead_U = Annotated[
    ApiRunnerEventRead | ApiRunEventRead | ApiSimulatorOutputEventRead,
    Field(discriminator="event_discriminator"),
]

ApiEventUpdate_U = Annotated[
    ApiRunnerEventUpdate | ApiRunEventUpdate, Field(discriminator="event_discriminator")
]

ApiEventDelete_U = Annotated[
    ApiRunnerEventDelete | ApiRunEventDelete | ApiSimulatorOutputEventDelete,
    Field(discriminator="event_discriminator"),
]

ApiEventQuery_U = Annotated[
    ApiRunnerEventQuery | ApiRunEventQuery, Field(discriminator="event_discriminator")
]

BundleEventUnion_T = TypeVar(
    "BundleEventUnion_T",
    bound=ApiEventCreate_U | ApiEventRead_U | ApiEventUpdate_U | ApiEventDelete_U | ApiEventQuery_U,
)


class ApiEventBundle(BaseModel, Generic[BundleEventUnion_T]):
    events: dict[str, list[BundleEventUnion_T]] = {}
    """
    A dict that bundles events of different types in a dict. Each type is 
    associated with a bundle of events of that specific type.
    """

    def add_event(self, event: BundleEventUnion_T) -> None:
        if event.event_discriminator not in self.events:
            self.events[event.event_discriminator] = []
        self.events[event.event_discriminator].append(event)

    def add_events(self, *args: tuple[BundleEventUnion_T]):
        for event in args:
            self.add_event(event)


"""
Type Adapters useful for validation etc. 
"""
EventCreate_A = TypeAdapter(ApiEventCreate_U)

ApiRunnerEventCreate_List_A = TypeAdapter(list[ApiRunnerEventCreate])
ApiRunEventCreate_List_A = TypeAdapter(list[ApiRunEventCreate])
ApiSimulatorOutputEventCreate_List_A = TypeAdapter(list[ApiRunEventCreate])


EventRead_A = TypeAdapter(ApiEventRead_U)
ApiRunnerEventRead_List_A = TypeAdapter(list[ApiRunnerEventRead])
ApiRunEventRead_List_A = TypeAdapter(list[ApiRunEventRead])
ApiSimulatorOutputEventRead_List_A = TypeAdapter(list[ApiSimulatorOutputEventRead])


EventUpdate_A = TypeAdapter(ApiEventUpdate_U)
ApiRunnerEventUpdate_List_A = TypeAdapter(list[ApiRunnerEventUpdate])
ApiRunEventUpdate_List_A = TypeAdapter(list[ApiRunEventUpdate])


EventDelete_A = TypeAdapter(ApiEventDelete_U)
ApiRunnerEventDelete_List_A = TypeAdapter(list[ApiRunnerEventDelete])
ApiRunEventDelete_List_A = TypeAdapter(list[ApiRunEventDelete])
ApiSimulatorOutputEventDelete_List_A = TypeAdapter(list[ApiSimulatorOutputEventDelete])


ApiRunnerEventQuery_List_A = TypeAdapter(list[ApiRunnerEventQuery])
ApiRunEventQuery_List_A = TypeAdapter(list[ApiRunEventQuery])


# TODO: FIXME
class ApiEventQuery(BaseModel):
    event_discriminator: str
    ids: list[int] | None = None
    runner_ids: list[int] | None = None
    run_ids: list[int] | None = None
    simulation_ids: list[int] | None = None
    proxy_ids: list[int] | None = None
    event_status: list[ApiEventStatus] | None = None
    runner_event_type: list[RunnerEventType] | None = None
    run_event_type: list[RunEventType] | None = None
    limit: int | None = None


if __name__ == "__main__":
    c_bundle = ApiEventBundle[ApiEventCreate_U]()
    c1 = ApiRunnerEventCreate(runner_id=3)
    c2 = ApiRunnerEventCreate(runner_id=2)
    c3 = ApiRunnerEventCreate(runner_id=3)
    cr1 = ApiRunEventCreate(runner_id=3, run_id=2, run_event_type=RunEventType.simulation_status)
    c_bundle.add_events(c1, c2, c3)
    c_bundle.add_event(cr1)
    d = c_bundle.model_dump()
    b = ApiEventBundle[ApiEventCreate_U].model_validate(d)
    print(b)

    r_bundle = ApiEventBundle[ApiEventRead_U]()
    r_bundle.add_event(
        ApiSimulatorOutputEventRead(
            id=4,
            runner_id=3,
            run_id=4,
            simulation_id=5,
            output="",
            simulator_id=7324,
            is_stderr=False,
        )
    )
    d = r_bundle.model_dump()
    b = ApiEventBundle[ApiEventRead_U].model_validate(d)
    for ty, lis in b.events.items():
        print(f"{ty} ==> {lis}")

    oe = ApiSimulatorOutputEventCreate(
        runner_id=3,
        run_id=4,
        simulation_id=23,
        simulator_id=23,
        output="kabfkjdsbfkdjb",
        is_stderr=False,
    )
    col = ApiConsoleOutputLine.model_validate(oe)
