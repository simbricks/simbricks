import socket
import subprocess
import typing as tp
from simbricks.runner.main_runner.plugins import plugin

class SimbricksDockerPlugin(plugin.FragmentRunnerPlugin):

    def __init__(self):
        super().__init__()
        self.docker_container_id: str | None = None
        self.fragment_socket: socket.socket | None = None

    @staticmethod
    def name():
        return "SimbricksDockerRunner"

    @staticmethod
    def ephemeral():
        return False

    async def read(self, length: int) -> str:
        if self.fragment_socket is None:
            return ""
        chunks = []
        received_bytes = 0
        while received_bytes < length:
            chunk = self.fragment_socket.recv(min(length - received_bytes, 2048))
            if chunk == b"":
                # TODO: raise exception instead?
                return ""
            chunks.append(chunk)
            received_bytes += len(chunk)
        return (b"".join(chunks)).decode("utf-8")

    async def write(self) -> bool:
        pass

    async def start(self):
        print("start simbricks docker runner")
        # create a TCP socket for a connection between the main-runner and fragment-runner
        serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversock.bind(("127.0.0.1", 0))
        serversock.listen(1)

        # start the docker container with the fragment-runner
        # docker_run = subprocess.run(["docker", "run", "-d", "simbricks/local-runner"])
        # docker_run.check_returncode()
        # self.docker_container_id = str(docker_run.stdout.strip())
        runner_run = subprocess.Popen(["python", "/workspaces/simbricks/runner.py", "127.0.0.1", f"{serversock.getsockname()[1]}"])

        # wait for the fragment-runner to connect
        # TODO: add a timeout and fail if no connection has been established
        (clientsock, address) = serversock.accept()
        serversock.close()
        self.fragment_socket = clientsock


    async def stop(self):
        print("stop simbricks docker runner")
        if self.docker_container_id is None:
            return
        docker_stop = subprocess.run(["docker", "container", "stop", self.docker_container_id])
        if docker_stop.returncode != 0:
            print(f"WARNING: could not stop docker container {self.docker_container_id}")

runner_plugin = SimbricksDockerPlugin