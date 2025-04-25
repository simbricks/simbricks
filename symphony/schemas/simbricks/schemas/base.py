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
from typing import TypeVar, Generic, Literal, Annotated, Any, Type, Callable
from pydantic import BaseModel, TypeAdapter, Field, field_serializer


class ApiNamespace(BaseModel):
    id: int | None = None
    parent_id: int | None = None
    name: str
    base_path: str | None = None


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
    object_id: int | None = None
    instantiation_id: int | None = None
    cores_required: int | None = None
    memory_required: int | None = None
    runner_tags: list[str] | None = None
    fragment_executor_tag: str | None = None


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
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            ranking = {
                RunState.SPAWNED: 1,
                RunState.PENDING: 2,
                RunState.RUNNING: 3,
                RunState.COMPLETED: 4,
                RunState.ERROR: 5,
                RunState.CANCELLED: 6,
            }
            return ranking[self] > ranking[other]
        return NotImplemented

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self > other or self == other
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return not (self >= other)
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return not (self > other)
        return NotImplemented

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


class RunnerStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    OFFLINE = "OFFLINE"


class ApiRunner(BaseModel):
    id: int | None = None
    label: str | None = None
    namespace_id: int | None = None
    resource_group_id: int | None = None
    status: RunnerStatus | None = None
    tags: list[ApiRunnerTag] = []
    plugin_tags: list[ApiRunnerTag] = []


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


class RunComponentState(str, enum.Enum):
    UNKNOWN = "unknown"
    PREPARING = "preparing"
    STARTING = "starting"
    RUNNING = "running"
    TERMINATED = "terminated"


class ApiSimulatorState(BaseModel):
    run_id: int
    simulator_id: int
    simulator_name: str | None = None
    command: str | None = None
    state: RunComponentState | None = None


class ApiProxyState(BaseModel):
    run_id: int
    proxy_id: int
    proxy_name: str | None = None
    ip: str | None = None
    port: int | None = None
    command: str | None = None
    state: RunComponentState | None = None


class ApiConsoleOutputLine(BaseModel):
    id: int | None = None
    produced_at: datetime.datetime
    output: str
    is_stderr: bool


class ApiRunSimulatorOutput(BaseModel):
    run_id: int
    simulator_id: int
    output_lines: list[ApiConsoleOutputLine] = []


class ApiRunProxyOutput(BaseModel):
    run_id: int
    proxy_id: int
    output_lines: list[ApiConsoleOutputLine] = []


class ApiRunComponent(BaseModel):
    name: str
    commands: dict[str, list[ApiConsoleOutputLine]] = {}


class ApiRunOutput(BaseModel):
    run_id: int
    simulators: dict[int, ApiRunComponent] = {}
    proxies: dict[int, ApiRunComponent] = {}


class ApiRunOutputFilter(BaseModel):
    simulator_seen_until_line_id: int | None = None
    proxy_seen_until_line_id: int | None = None


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
    Must be OVERWRITTEN as Literal IN SUBCLASSES (see the helper classes below).
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


class ApiCreateEvent(AbstractApiEvent):
    id: None = None


class ApiReadEvent(AbstractApiEvent):
    pass


class ApiUpdateEvent(AbstractApiEvent):
    pass


class ApiDeleteEvent(AbstractApiEvent):
    pass


class AbstractApiEventQuery(BaseModel, abc.ABC):
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


class AbstractApiRunnerEvent(AbstractApiEvent):
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
    runner_event_type: RunnerEventType | None = None


class ApiRunnerEventDelete(ApiDeleteEvent):
    event_discriminator: Literal["ApiRunnerEventDelete"] = "ApiRunnerEventDelete"


class ApiRunnerEventQuery(AbstractApiEventQuery):
    event_discriminator: Literal["ApiRunnerEventQuery"] = "ApiRunnerEventQuery"
    runner_ids: list[int] | None = None
    runner_event_type: list[RunnerEventType] | None = None


class AbstractApiOutputEvent:
    output_generated_at: datetime.datetime
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

    @field_serializer("output_generated_at")
    def serialize_output_generated_at(self, dt: datetime.datetime, _info) -> str:
        return dt.isoformat()


""" ############################################################################
Run related events
"""  ############################################################################


class RunEventType(str, enum.Enum):
    KILL = "KILL"
    SIMULATION_STATUS = "SIMULATION_STATUS"
    START_RUN = "START_RUN"


class AbstractApiRunEvent(AbstractApiEvent):
    runner_id: int  # TODO: considering fragments etc. we may want to remove this again
    """
    The runner the run is associated with.
    """
    run_id: int
    """
    The run associated with.
    """
    run_event_type: RunEventType
    """
    The kind of runner specific event this is (e.g. KILL).  
    """


class ApiRunEventCreate(ApiCreateEvent, AbstractApiRunEvent):
    event_discriminator: Literal["ApiRunEventCreate"] = "ApiRunEventCreate"


class ApiRunEventRead(ApiReadEvent, AbstractApiRunEvent):
    event_discriminator: Literal["ApiRunEventRead"] = "ApiRunEventRead"


class ApiRunEventStartRunRead(ApiRunEventRead):
    run_event_type: RunEventType = RunEventType.START_RUN
    event_discriminator: Literal["ApiRunEventStartRunRead"] = "ApiRunEventStartRunRead"

    fragments: list[tuple[int, str | None]]
    """
    A list of tuples of fragment IDs and fragment executor tags. Those are the IDs from the Fragment
    Python objects stored in the instantiation.
    """
    inst: Any = None
    inst_id: int | None = None
    system: Any = None
    simulation: Any = None

    inst_input_artifact: str | None = None
    fragment_input_artifact: str | None = None


class ApiRunEventUpdate(ApiUpdateEvent, AbstractApiRunEvent):
    event_discriminator: Literal["ApiRunEventUpdate"] = "ApiRunEventUpdate"
    run_event_type: RunEventType | None = None


class ApiRunEventDelete(ApiDeleteEvent):
    event_discriminator: Literal["ApiRunEventDelete"] = "ApiRunEventDelete"


class ApiRunEventQuery(AbstractApiEventQuery):
    event_discriminator: Literal["ApiRunEventQuery"] = "ApiRunEventQuery"
    runner_ids: list[int] | None = None
    run_ids: list[int] | None = None
    run_event_type: list[RunEventType] | None = None


class ApiRunEventStartRunQuery(AbstractApiEventQuery):
    event_discriminator: Literal["ApiRunEventStartRunQuery"] = "ApiRunEventStartRunQuery"
    runner_ids: list[int] | None = None
    run_ids: list[int] | None = None
    run_event_type: RunEventType = RunEventType.START_RUN


""" ############################################################################
Run fragment related events
"""  ############################################################################


class AbstractApiRunFragmentEvent(AbstractApiEvent):
    run_id: int
    """
    The associated run.
    """
    fragment_id: int
    """
    The associated fragment.
    """


class AbstractApiRunFragmentStateEvent(AbstractApiRunFragmentEvent):
    run_state: RunState
    """
    The state of the run for this fragment.
    """


class ApiRunFragmentStateEventCreate(ApiCreateEvent, AbstractApiRunFragmentStateEvent):
    event_discriminator: Literal["ApiRunFragmentStateEventCreate"] = (
        "ApiRunFragmentStateEventCreate"
    )


class AbstractApiRunFragmentOutputArtifactEvent(AbstractApiRunFragmentEvent):
    output_artifact: str
    output_artifact_name: str
    """
    The output artifact of the run for this fragment.
    """


class ApiRunFragmentOutputArtifactEventCreate(
    ApiCreateEvent, AbstractApiRunFragmentOutputArtifactEvent
):
    event_discriminator: Literal["ApiRunFragmentOutputArtifactEventCreate"] = (
        "ApiRunFragmentOutputArtifactEventCreate"
    )


""" ############################################################################
Simulator related events
"""  ############################################################################


class AbstractApiSimulatorEvent(AbstractApiEvent):
    run_id: int
    """
    The run a fragment is associated with.
    """
    simulator_id: int
    """
    The simulator id from the experiment definition the event is associated with.
    """


class AbstractApiSimulatorStateChangeEvent(AbstractApiSimulatorEvent):
    simulator_state: RunComponentState
    """
    The current state of the simulator.
    """
    simulator_name: str | None = None
    """
    The name of the simulator.
    """
    command: str | None = None
    """
    The command associated with the state change.
    """


class ApiSimulatorStateChangeEventCreate(ApiCreateEvent, AbstractApiSimulatorStateChangeEvent):
    event_discriminator: Literal["ApiSimulatorStateChangeEventCreate"] = (
        "ApiSimulatorStateChangeEventCreate"
    )


class ApiSimulatorStateChangeEventRead(ApiReadEvent, AbstractApiSimulatorStateChangeEvent):
    event_discriminator: Literal["ApiSimulatorStateChangeEventRead"] = (
        "ApiSimulatorStateChangeEventRead"
    )


class ApiSimulatorStateChangeEventQuery(AbstractApiEventQuery):
    event_discriminator: Literal["ApiSimulatorStateChangeEventQuery"] = (
        "ApiSimulatorStateChangeEventQuery"
    )
    run_ids: list[int] | None = None
    simulator_ids: list[int] | None = None
    simulator_names: list[str] | None = None
    simulator_states: list[RunComponentState] | None = None


class ApiSimulatorOutputEventCreate(
    ApiCreateEvent, AbstractApiSimulatorEvent, AbstractApiOutputEvent
):
    event_discriminator: Literal["ApiSimulatorOutputEventCreate"] = "ApiSimulatorOutputEventCreate"


class ApiSimulatorOutputEventRead(ApiReadEvent, AbstractApiSimulatorEvent, AbstractApiOutputEvent):
    event_discriminator: Literal["ApiSimulatorOutputEventRead"] = "ApiSimulatorOutputEventRead"
    run_id: int | None = None
    simulator_id: int | None = None


class ApiSimulatorOutputEventDelete(ApiDeleteEvent):
    event_discriminator: Literal["ApiSimulatorOutputEventDelete"] = "ApiSimulatorOutputEventDelete"


"""
Proxy related events
"""


class AbstractApiProxyEvent(AbstractApiEvent):
    run_id: int
    """
    The run a fragment is associated with.
    """
    proxy_id: int
    """
    the proxy id the event is associated with. Note that this is the python objects id and not those
    of the database table. For details see 'IdObj'.
    """


class AbstractApiProxyStateChangeEvent(AbstractApiProxyEvent):
    proxy_name: str
    """The name of the proxy."""
    proxy_state: RunComponentState
    """
    The current state of the proxy.
    """
    proxy_ip: str
    """The IP the proxy is listening on / connecting to."""
    proxy_port: int
    """The port the proxy is listening on / connecting to."""
    command: str | None = None
    """
    The command associated with the state change.
    """


class ApiProxyStateChangeEventCreate(ApiCreateEvent, AbstractApiProxyStateChangeEvent):
    event_discriminator: Literal["ApiProxyStateChangeEventCreate"] = (
        "ApiProxyStateChangeEventCreate"
    )


class ApiProxyStateChangeEventRead(ApiReadEvent, AbstractApiProxyStateChangeEvent):
    event_discriminator: Literal["ApiProxyStateChangeEventRead"] = "ApiProxyStateChangeEventRead"


class ApiProxyStateChangeEventQuery(AbstractApiEventQuery):
    event_discriminator: Literal["ApiProxyStateChangeEventQuery"] = "ApiProxyStateChangeEventQuery"
    run_ids: list[int] | None = None
    proxy_ids: list[int] | None = None
    proxy_names: list[str] | None = None
    proy_states: list[RunComponentState] | None = None
    proxy_ips: list[str] | None = None
    proxy_ports: list[int] | None = None


class ApiProxyOutputEventCreate(ApiCreateEvent, AbstractApiProxyEvent, AbstractApiOutputEvent):
    event_discriminator: Literal["ApiProxyOutputEventCreate"] = "ApiProxyOutputEventCreate"


class ApiProxyOutputEventRead(ApiReadEvent, AbstractApiProxyEvent, AbstractApiOutputEvent):
    event_discriminator: Literal["ApiProxyOutputEventRead"] = "ApiProxyOutputEventRead"
    run_id: int | None = None
    proxy_id: int | None = None


class ApiProxyOutputEventDelete(ApiDeleteEvent):
    event_discriminator: Literal["ApiProxyOutputEventDelete"] = "ApiProxyOutputEventDelete"


"""
ApiEventBundle definitions.
"""


class ApiEventType(enum.Enum):
    ApiEventCreate = "ApiEventCreate"
    ApiEventRead = "ApiEventRead"
    ApiEventUpdate = "ApiEventUpdate"
    ApiEventDelete = "ApiEventDelete"
    ApiEventQuery = "ApiEventQuery"

    def get_type(self):
        match self:
            case ApiEventType.ApiEventCreate:
                return ApiEventCreate_U
            case ApiEventType.ApiEventRead:
                return ApiEventRead_U
            case ApiEventType.ApiEventUpdate:
                return ApiEventUpdate_U
            case ApiEventType.ApiEventDelete:
                return ApiEventDelete_U
            case ApiEventType.ApiEventQuery:
                return ApiEventQuery_U


ApiEventCreate_U = Annotated[
    ApiRunnerEventCreate
    | ApiRunEventCreate
    | ApiSimulatorOutputEventCreate
    | ApiSimulatorStateChangeEventCreate
    | ApiProxyStateChangeEventCreate
    | ApiProxyOutputEventCreate
    | ApiRunFragmentStateEventCreate,
    Field(discriminator="event_discriminator"),
]

ApiEventRead_U = Annotated[
    ApiRunnerEventRead
    | ApiRunEventRead
    | ApiRunEventStartRunRead
    | ApiSimulatorOutputEventRead
    | ApiSimulatorStateChangeEventRead
    | ApiProxyStateChangeEventRead
    | ApiProxyOutputEventRead,
    Field(discriminator="event_discriminator"),
]

ApiEventUpdate_U = Annotated[
    ApiRunnerEventUpdate | ApiRunEventUpdate,
    Field(discriminator="event_discriminator"),
]

ApiEventDelete_U = Annotated[
    ApiRunnerEventDelete | ApiRunEventDelete | ApiSimulatorOutputEventDelete,
    Field(discriminator="event_discriminator"),
]

ApiEventQuery_U = Annotated[
    ApiRunnerEventQuery
    | ApiRunEventQuery
    | ApiRunEventStartRunQuery
    | ApiSimulatorStateChangeEventQuery
    | ApiProxyStateChangeEventQuery,
    Field(discriminator="event_discriminator"),
]

BundleEventUnion_T = TypeVar(
    "BundleEventUnion_T",
    bound=ApiEventCreate_U | ApiEventRead_U | ApiEventUpdate_U | ApiEventDelete_U | ApiEventQuery_U,
)


class ApiEventBundle(BaseModel, Generic[BundleEventUnion_T]):
    events: dict[str, list[BundleEventUnion_T]] = {}
    """
    This bundle is supposed to bundle events. Bundling means that in instances of this class a mapping 
    is stored in the following form: 'event_discriminator' -> list[Event]. For this reason, all events 
    that shall be used with this bundle must overwrite the 'event_discriminator' literal and set it 
    to a unique value. Having this mapping allows to not only bundle events of the same type, but to 
    bundle events of multiple types. 
    
    This allows to 1) bundle multiple events of the same type to send e.g. multiple 'ApiSimulatorOutputEventCreate'
    with one request to the backend. Besides, it allows to send multiple such bundles of different types 
    to the backend, meaning that a 'ApiSimulatorOutputEventCreate' as well as 'ApiRunEventCreate' and 
    a 'ApiRunnerEventCreate' bundle can each be send to the backend within a single request.

    NOTE: Event thought this bundling allows to store bundles of different events, it shall always be 
    used only with the types defined in one of the CRUD unions defined above at a time. That means
    'update' events SHALL NOT be bundled together with cerate or delete events (even though this would 
    be possible). The reason is that we want to keep a distinction between such CRUD operations in our
    API, thus we advise not to bundle events in that way (this will also not be supported by our backend
    API).
    """

    def empty(self) -> bool:
        return len(self.events) == 0

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

Model_Class_T = TypeVar("Model_Class_T")


def validate_list_type(
    model_list: list[BundleEventUnion_T], model_class: Type[Model_Class_T]
) -> list[Model_Class_T]:
    adapter = TypeAdapter(list[Model_Class_T])
    validated_model_list = adapter.validate_python(model_list)
    return validated_model_list


Source_Class_T = TypeVar("Source_Class_T")
Target_Class_T = TypeVar("Target_Class_T")


def convert_validate_type(
    source: list[Source_Class_T], target: Type[Target_Class_T]
) -> list[Target_Class_T]:
    assert isinstance(target, type) and issubclass(target, BaseModel)
    converted = []
    for mod in source:
        assert isinstance(mod, BaseModel)
        dump = mod.model_dump()
        conv = target.model_validate(dump)
        converted.append(conv)
    return converted


def convert_validate_factory(
    source: list[Source_Class_T], factory: Callable[[Source_Class_T], Target_Class_T]
) -> list[Target_Class_T]:
    converted = []
    for mod in source:
        assert isinstance(mod, BaseModel)
        conv = factory(mod)
        converted.append(conv)
    return converted


"""
The following type adapters are deprecated. Use aboves 'generic' methods instead.
"""

ApiRunnerEventCreate_List_A = TypeAdapter(list[ApiRunnerEventCreate])
ApiRunEventCreate_List_A = TypeAdapter(list[ApiRunEventCreate])
ApiSimulatorOutputEventCreate_List_A = TypeAdapter(list[ApiSimulatorOutputEventCreate])
ApiSimulatorStateChangeEventCreate_List_A = TypeAdapter(list[ApiSimulatorStateChangeEventCreate])
ApiProxyOutputEventCreate_List_A = TypeAdapter(list[ApiProxyOutputEventCreate])
ApiProxyStateChangeEventCreate_List_A = TypeAdapter(list[ApiProxyStateChangeEventCreate])

EventRead_A = TypeAdapter(ApiEventRead_U)
ApiRunnerEventRead_List_A = TypeAdapter(list[ApiRunnerEventRead])
ApiRunEventRead_List_A = TypeAdapter(list[ApiRunEventRead])
ApiSimulatorOutputEventRead_List_A = TypeAdapter(list[ApiSimulatorOutputEventRead])
ApiSimulatorStateChangeEventRead_List_A = TypeAdapter(list[ApiSimulatorStateChangeEventRead])
ApiProxyOutputEventRead_List_A = TypeAdapter(list[ApiProxyOutputEventRead])
ApiProxyStateChangeEventRead_List_A = TypeAdapter(list[ApiProxyStateChangeEventRead])

EventUpdate_A = TypeAdapter(ApiEventUpdate_U)
ApiRunnerEventUpdate_List_A = TypeAdapter(list[ApiRunnerEventUpdate])
ApiRunEventUpdate_List_A = TypeAdapter(list[ApiRunEventUpdate])

EventDelete_A = TypeAdapter(ApiEventDelete_U)
ApiRunnerEventDelete_List_A = TypeAdapter(list[ApiRunnerEventDelete])
ApiRunEventDelete_List_A = TypeAdapter(list[ApiRunEventDelete])
ApiSimulatorOutputEventDelete_List_A = TypeAdapter(list[ApiSimulatorOutputEventDelete])
ApiProxyOutputEventDelete_List_A = TypeAdapter(list[ApiProxyOutputEventDelete])

ApiRunnerEventQuery_List_A = TypeAdapter(list[ApiRunnerEventQuery])
ApiRunEventQuery_List_A = TypeAdapter(list[ApiRunEventQuery])
