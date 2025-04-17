import asyncio
import re
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

        default_params: dict[str, tp.Any] = {
            "listen_ip": "0.0.0.0",
            "docker_image": "simbricks/simbricks-executor",
            "docker_pull": False,
        }

        listen_ip = plugin.get_first_match("listen_ip", config_params, default_params)
        assert listen_ip is not None
        self.server = await asyncio.start_server(self.accept_connection, listen_ip)

        docker_image = plugin.get_first_match(
            "docker_image", fragment_params, config_params, default_params
        )
        assert docker_image is not None

        if "docker_image_allow" in config_params:
            allow_list = config_params["docker_image_allow"]
            if not isinstance(allow_list, list):
                raise RuntimeError("invalid format of docker_image_allow list")
            for allow_exp in allow_list:
                if re.fullmatch(allow_exp, docker_image) is not None:
                    break
            else:
                raise RuntimeError(f"docker_image is not in allow list")

        if "docker_image_deny" in config_params:
            deny_list = config_params["docker_image_deny"]
            if not isinstance(deny_list, list):
                raise RuntimeError("invalid format of docker_image_deny list")
            for deny_exp in deny_list:
                if re.fullmatch(deny_exp, docker_image) is not None:
                    raise RuntimeError(f"docker_image is in deny list")

        docker_pull = plugin.get_first_match("docker_pull", config_params, default_params)
        assert isinstance(docker_pull, bool)
        if docker_pull:
            pull = subprocess.run(["docker", "pull", docker_image])
            if pull.returncode != 0:
                raise RuntimeError(f"docker pull of image {docker_image} failed")

        port = self.server.sockets[0].getsockname()[1]
        self.executor = subprocess.Popen([
            "docker", "run", "--rm", "--device=/dev/kvm",
            "--add-host=host.docker.internal:host-gateway",
            docker_image,
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