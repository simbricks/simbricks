import asyncio
import subprocess
import typing as tp

from simbricks.runner.main_runner.plugins import plugin

class SimbricksDockerPlugin(plugin.FragmentRunnerPlugin):

    def __init__(self):
        super().__init__()
        self.executor: subprocess.Popen | None = None
        self.server: asyncio.Server | None = None
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.connected = asyncio.Event()

    @staticmethod
    def name():
        return "SimbricksDockerRunner"

    async def read(self, length: int) -> bytes:
        data = await self.reader.read(length)
        if length != 0 and len(data) == 0:
            raise RuntimeError("connection broken")
        return data

    async def write(self, data: bytes) -> None:
        self.writer.write(data)
        await self.writer.drain()

    def accept_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        assert self.reader is None
        assert self.writer is None
        self.reader = reader
        self.writer = writer
        self.server.close()
        self.connected.set()

    async def start(
        self, config_params: dict[tp.Any, tp.Any], fragment_params: dict[tp.Any, tp.Any]
    ) -> None:
        print("start simbricks docker fragment executor")
        self.server = await asyncio.start_server(self.accept_connection, "0.0.0.0")

        port = self.server.sockets[0].getsockname()[1]
        self.executor = subprocess.Popen([
            "docker", "run", "--rm", "--device=/dev/kvm",
            "--add-host=host.docker.internal:host-gateway",
            "simbricks/simbricks-executor",
            "host.docker.internal", str(port)])

        # wait for the fragment executor to connect
        await self.connected.wait()

    async def stop(self):
        print("stop simbricks docker fragment executor")
        if self.executor is None:
            return

        self.writer.close()
        await self.writer.wait_closed()
        await self.server.wait_closed()

        self.executor.wait()
        self.executor = None
        print("successfully stopped docker fragment executor")

runner_plugin = SimbricksDockerPlugin