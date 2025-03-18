import abc

from simbricks.schemas import base as schemas

class FragmentRunnerPlugin(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    def name() -> str:
        pass

    @staticmethod
    @abc.abstractmethod
    def ephemeral() -> bool:
        pass

    @abc.abstractmethod
    async def start(self) -> None:
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
        events_json = events.model_dump_json()
        payload = bytes(f"{event_type.value},{events_json}", encoding="utf-8")
        data = bytes(f"{len(payload):12x}", encoding="utf-8") + payload
        # TODO: error handling
        self.write(data)

    async def get_events(self) -> tuple[schemas.ApiEventType, schemas.ApiEventBundle]:
        try:
            length_str = (await self.read(12)).decode("utf-8")
            length = int(length_str, 16)
            payload = (await self.read(length)).decode("utf-8")
        except Exception:
            #TODO
            pass

        separator = payload.find(",")
        if separator == -1:
            raise RuntimeError("invalid format of event bundle payload")

        event_type = schemas.ApiEventType(payload[:separator])
        events_json = payload[separator+1:]
        events = schemas.ApiEventBundle[event_type.get_type()].model_validate_json(events_json)

        return (event_type, events)