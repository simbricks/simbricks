# Copyright 2022 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from simbricks.orchestration import simulation
import enum
import pathlib


class SockType(enum.Enum):
    LISTEN = enum.auto()
    CONNECT = enum.auto()


class Socket:

    def __init__(self, path: str = "", ty: SockType = SockType.LISTEN):
        self._path = path
        self._type = ty


class InstantiationEnvironment:

    def __init__(
        self,
        repo_path: str = pathlib.Path(__file__).parents[3].resolve(),
        workdir: str = pathlib.Path(),
        cpdir: str = pathlib.Path(),
    ):
        # TODO: add more parameters that wont change during instantiation
        self._repodir: str = pathlib.Path(repo_path).absolute()
        self._workdir: str = pathlib.Path(workdir).absolute()
        self._cpdir: str = pathlib.Path(cpdir).absolute()


class Instantiation:

    def __init__(
        self, simulation, env: InstantiationEnvironment = InstantiationEnvironment()
    ):
        self._simulation = simulation
        self._env: InstantiationEnvironment = env
        self._socket_tracker: set[tuple[simulation.channel.Channel, SockType]] = set()

    def get_socket_path(self, chan: simulation.channel.Channel) -> Socket:

        # TODO: use self._socket_tracker to determine socket type that is needed
        sock_type = SockType.LISTEN

        # TODO: generate socket path
        sock_path = ""

        return Socket(sock_path, sock_type)

    @staticmethod
    def is_absolute_exists(path: str) -> bool:
        path = pathlib.Path(path)
        return path.is_absolute() and path.is_file()

    # TODO: add more methods constructing paths as required by methods in simulators or image handling classes

    def hd_path(self, hd_name_or_path: str) -> str:
        if Instantiation.is_absolute_exists(hd_name_or_path):
            return hd_name_or_path

        path = pathlib.Path(
            f"{self._env._repodir}/images/output-{hd_name_or_path}/{hd_name_or_path}"
        )

        return path.absolute()

    def dynamic_img_path(self, format: str) -> str:
        # TODO
        return ""
