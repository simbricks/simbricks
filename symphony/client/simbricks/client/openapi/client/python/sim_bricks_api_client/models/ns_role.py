from enum import Enum


class NsRole(str, Enum):
    OWNER = "owner"
    USER = "user"

    def __str__(self) -> str:
        return str(self.value)
