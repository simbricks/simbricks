import datetime
import enum

from pydantic import BaseModel


class ApiSystem(BaseModel):
    id: int | None = None
    sb_json: str | dict | None = None
    namespace_id: int | None = None


class ApiSystemQuery(BaseModel):
    namespace_id: int | None = None
    limit: int | None = None


class ApiSimulation(BaseModel):
    id: int | None = None
    namespace_id: int = None
    system_id: int = None
    sb_json: str | dict | None = None


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


class ApiInstantiationQuery(BaseModel):
    id: int | None = None
    simulation_id: int | None = None
    fragments: list[ApiFragmentQuery] = []
    limit: int | None = None


class RunState(enum.Enum):
    SPAWNED = "spawned"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ApiRun(BaseModel):
    id: int | None
    namespace_id: int | None = None
    instantiation_id: int | None = None
    state: RunState | None = None
    output: str | None = None


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


class ApiRunnerTag(BaseModel):
    label: str


class ApiRunner(BaseModel):
    id: int | None = None
    label: str | None = None
    namespace_id: int | None = None
    resource_group_id: int | None = None
    tags: list[ApiRunnerTag] = []


class RunnerEventAction(enum.Enum):
    KILL = "kill"
    HEARTBEAT = "heartbeat"
    SIMULATION_STATUS = "simulation_status"
    START_RUN = "start_run"


class RunnerEventStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ApiRunnerEvent(BaseModel):
    id: int | None = None
    action: RunnerEventAction | None = None
    run_id: int | None = None
    runner_id: int
    event_status: RunnerEventStatus | None = None


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


class RunSimulatorState(enum.Enum):
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
