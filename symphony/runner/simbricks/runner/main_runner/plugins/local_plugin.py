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

    async def start(self):
        print("start simbricks local runner")
        self.server = await asyncio.start_server(self.accept_connection, "127.0.0.1")
        port = self.server.sockets[0].getsockname()[1]

        self.executor = subprocess.Popen(["simbricks-executor-local", "127.0.0.1", str(port)])

        # wait for the fragment executor to connect
        await self.connected.wait()

    async def stop(self):
        print("stop simbricks local runner")
        if self.executor is None:
            return
        self.executor.terminate()
        self.executor.wait()
        self.executor = None
        await self.server.wait_closed()
        print("successfully stopped local fragment executor")

runner_plugin = SimbricksLocalPlugin