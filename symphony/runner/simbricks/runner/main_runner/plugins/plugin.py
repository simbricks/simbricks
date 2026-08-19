import abc
import typing as tp

from simbricks.client.namespace import EventFromRunner_U, EventToRunner_U
from simbricks.runner import artifacts, framing


class FragmentRunnerPlugin(abc.ABC):
    def __init__(self) -> None:
        self._channel = framing.FrameChannel(self.read, self.write)
        self._artifact_sink = artifacts.RelayArtifactSink(self._channel)

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
        await self._channel.send(framing.EventFrame.pack(events))

    async def send_artifact(self, artifact: artifacts.Artifact) -> None:
        await self._artifact_sink.store(artifact)

    async def read_frame(self) -> framing.Frame:
        return await self._channel.receive()

    def decode_events(self, frame: framing.EventFrame) -> list[EventFromRunner_U]:
        # This connection only ever receives events produced by the fragment
        # runner; EventFrame.unpack' return type is broader.
        return tp.cast(list[EventFromRunner_U], frame.unpack())


def get_first_match(key: tp.Any, *params: dict[tp.Any, tp.Any]) -> tp.Any | None:
    for param in params:
        if key in param:
            return param[key]
    return None
