import abc
import typing as tp

from simbricks.client.namespace import EventFromRunner_U, EventToRunner_U
from simbricks.runner import utils


class FragmentRunnerPlugin(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def name() -> str:
        raise RuntimeError("cannot call 'name' on abstract FragmentRunnerPlugin")

    @abc.abstractmethod
    async def start(
        self, config_params: dict[tp.Any, tp.Any], fragment_params: dict[tp.Any, tp.Any]
    ) -> None:
        pass

    @abc.abstractmethod
    async def stop(self) -> None:
        pass

    @abc.abstractmethod
    async def read(self, length: int) -> bytes:
        pass

    @abc.abstractmethod
    async def write(self, data: bytes) -> None:
        pass

    async def send_events(self, events: list[EventToRunner_U]) -> None:
        await utils.send_events(self.write, events)

    async def get_events(self) -> list[EventFromRunner_U]:
        # This connection receives events produced by the fragment runner (EventFromRunner_U);
        # utils.get_events' return type is broader because it deserializes either direction.
        return tp.cast(list[EventFromRunner_U], await utils.get_events(self.read))


def get_first_match(key: tp.Any, *params: dict[tp.Any, tp.Any]) -> tp.Any | None:
    for param in params:
        if key in param:
            return param[key]
    return None
