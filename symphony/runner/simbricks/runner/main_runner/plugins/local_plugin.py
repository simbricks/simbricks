import asyncio
import subprocess
from simbricks.runner.main_runner.plugins import plugin

class SimbricksLocalPlugin(plugin.FragmentRunnerPlugin):

    def __init__(self):
        super().__init__()
        self.executor: subprocess.Popen | None = None
        self.server: asyncio.Server | None = None
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.connected = asyncio.Event()

    @staticmethod
    def name():
        return "SimbricksLocalRunner"

    @staticmethod
    def ephemeral():
        return False

    async def read(self, length: int) -> bytes:
        return await self.reader.read(length)

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

    async def start(self):
        print("start simbricks local runner")
        self.server = await asyncio.start_server(self.accept_connection, "127.0.0.1", 9000)

        self.executor = subprocess.Popen(["python", "/workspaces/simbricks/symphony/runner/simbricks/runner/fragment_runner/local/__main__.py"])

        # wait for the fragment executor to connect
        await self.connected.wait()

    async def stop(self):
        print("stop simbricks local runner")
        if self.executor is None:
            return
        self.executor.terminate()
        self.executor.wait()
        await self.server.wait_closed()

runner_plugin = SimbricksLocalPlugin