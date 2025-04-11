import abc
import typing as tp

from simbricks.runner import utils
from simbricks.schemas import base as schemas

class FragmentRunnerPlugin(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    def name() -> str:
        pass

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

    async def send_events(
        self, events: schemas.ApiEventBundle, event_type: schemas.ApiEventType
    ) -> None:
        await utils.send_events(self.write, events, event_type)

    async def get_events(self) -> tuple[schemas.ApiEventType, schemas.ApiEventBundle]:
        return await utils.get_events(self.read)