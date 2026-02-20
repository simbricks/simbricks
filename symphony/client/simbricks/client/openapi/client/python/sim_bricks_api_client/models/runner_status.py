from enum import Enum


class RunnerStatus(str, Enum):
    HEALTHY = "healthy"
    OFFLINE = "offline"

    def __str__(self) -> str:
        return str(self.value)
