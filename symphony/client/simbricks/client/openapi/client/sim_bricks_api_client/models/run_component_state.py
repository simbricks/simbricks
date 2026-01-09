from enum import Enum


class RunComponentState(str, Enum):
    PREPARING = "preparing"
    RUNNING = "running"
    STARTING = "starting"
    TERMINATED = "terminated"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return str(self.value)
