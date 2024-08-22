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
from abc import (ABC, abstractmethod)
import io

if tp.TYPE_CHECKING:  # prevent cyclic import
    import simbricks.orchestration.system.host as host
    import simbricks.orchestration.experiment.experiment_environment as expenv


class Application(ABC):
    def __init__(self, h: host.Host) -> None:
        self.host = h


# Note AK: Maybe we can factor most of the duplicate calls with the host out
# into a separate module.
class LinuxApplication(ABC):
    def __init__(self, h: host.LinuxHost) -> None:
        self.host = h

    def run_cmds(self, env: expenv.ExpEnv) -> tp.List[str]:
        """Commands to run on node."""
        return self.app.run_cmds(self)

    def cleanup_cmds(self, env: expenv.ExpEnv) -> tp.List[str]:
        """Commands to run to cleanup node."""
        return []

    def config_files(self, env: expenv.ExpEnv) -> tp.Dict[str, tp.IO]:
        """
        Additional files to put inside the node, which are mounted under
        `/tmp/guest/`.

        Specified in the following format: `filename_inside_node`:
        `IO_handle_of_file`
        """
        return {}

    def prepare_pre_cp(self, env: expenv.ExpEnv) -> tp.List[str]:
        """Commands to run to prepare node before checkpointing."""
        return [
            'set -x',
            'export HOME=/root',
            'export LANG=en_US',
            'export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:' + \
                '/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"'
        ]

    def prepare_post_cp(self, env: expenv.ExpEnv) -> tp.List[str]:
        """Commands to run to prepare node after checkpoint restore."""
        return []

    def strfile(self, s: str) -> io.BytesIO:
        """
        Helper function to convert a string to an IO handle for usage in
        `config_files()`.

        Using this, you can create a file with the string as its content on the
        simulated node.
        """
        return io.BytesIO(bytes(s, encoding='UTF-8'))