from enum import Enum


class RunState(str, Enum):
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ERROR = "error"
    PENDING = "pending"
    RUNNING = "running"
    SPAWNED = "spawned"

    def __str__(self) -> str:
        return str(self.value)
