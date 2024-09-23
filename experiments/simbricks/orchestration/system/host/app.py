# Copyright 2024 Max Planck Institute for Software Systems, and
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

import typing as tp
import abc
import io
from simbricks.orchestration.experiment import experiment_environment as expenv

if tp.TYPE_CHECKING:
    from simbricks.orchestration.system.host import base

class Application(abc.ABC):
    def __init__(self, h: 'Host') -> None:
        self.host = h


# Note AK: Maybe we can factor most of the duplicate calls with the host out
# into a separate module.
class BaseLinuxApplication(abc.ABC):
    def __init__(self, h: 'LinuxHost') -> None:
        self.host = h
        self.start_delay: float | None = None
        self.end_delay: float | None = None
        self.wait = True

    @abc.abstractmethod
    def run_cmds(self, env: expenv.ExpEnv) -> list[str]:
        """Commands to run on node."""
        return []

    def cleanup_cmds(self, env: expenv.ExpEnv) -> list[str]:
        """Commands to run to cleanup node."""
        if self.end_delay is None:
            return []
        else:
            return [f'sleep {self.start_delay}']

    def config_files(self, env: expenv.ExpEnv) -> dict[str, tp.IO]:
        """
        Additional files to put inside the node, which are mounted under
        `/tmp/guest/`.

        Specified in the following format: `filename_inside_node`:
        `IO_handle_of_file`
        """
        return {}

    def prepare_pre_cp(self, env: expenv.ExpEnv) -> list[str]:
        """Commands to run to prepare node before checkpointing."""
        return []

    def prepare_post_cp(self, env: expenv.ExpEnv) -> list[str]:
        """Commands to run to prepare node after checkpoint restore."""
        if self.end_delay is None:
            return []
        else:
            return [f'sleep {self.end_delay}']

    def strfile(self, s: str) -> io.BytesIO:
        """
        Helper function to convert a string to an IO handle for usage in
        `config_files()`.

        Using this, you can create a file with the string as its content on the
        simulated node.
        """
        return io.BytesIO(bytes(s, encoding="UTF-8"))


class PingClient(BaseLinuxApplication):
    def __init__(self, h: 'LinuxHost', server_ip: str = '192.168.64.1') -> None:
        super().__init__(h)
        self.server_ip = server_ip

    def run_cmds(self, env: expenv.ExpEnv) -> tp.List[str]:
        return [f'ping {self.server_ip} -c 10']


class Sleep(BaseLinuxApplication):
    def __init__(self, h: 'LinuxHost', delay: float = 10) -> None:
        super().__init__(h)
        self.delay = delay

    def run_cmds(self, env: expenv.ExpEnv) -> tp.List[str]:
        return [f'sleep {self.delay}']


class NetperfServer(BaseLinuxApplication):
    def __init__(self, h: 'LinuxHost') -> None:
        super().__init__(h)

    def run_cmds(self, env: expenv.ExpEnv) -> tp.List[str]:
        return ['netserver', 'sleep infinity']


class NetperfClient(BaseLinuxApplication):
    def __init__(self, h: 'LinuxHost', server_ip: str = '192.168.64.1') -> None:
        super().__init__(h)
        self.server_ip = server_ip
        self.duration_tp = 10
        self.duration_lat = 10

    def run_cmds(self, env: expenv.ExpEnv) -> tp.List[str]:
        return [
            'netserver',
            'sleep 0.5',
            f'netperf -H {self.server_ip} -l {self.duration_tp}',
            (
                f'netperf -H {self.server_ip} -l {self.duration_lat} -t TCP_RR'
                ' -- -o mean_latency,p50_latency,p90_latency,p99_latency'
            )
        ]