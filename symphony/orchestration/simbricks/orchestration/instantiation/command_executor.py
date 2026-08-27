# Copyright 2026 Max Planck Institute for Software Systems, and
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

from __future__ import annotations

import abc
import sys
import typing

if typing.TYPE_CHECKING:
    from simbricks.orchestration.simulation import base as sim_base


class CommandExecutorFactoryBase(abc.ABC):
    """Runtime services an instantiation may use while it is being prepared.

    Implemented by the runtime's CommandExecutorFactory. Implementations must not
    reach a suspension point: these are called from cancellation handlers.
    """

    @abc.abstractmethod
    async def msg_info(self, msg: str) -> None:
        pass

    @abc.abstractmethod
    async def msg_warning(self, msg: str) -> None:
        pass

    @abc.abstractmethod
    async def msg_error(self, msg: str) -> None:
        pass

    @abc.abstractmethod
    async def exec_prepare_cmds(
        self, cmds: list[str], sim: sim_base.Simulator | None = None
    ) -> None:
        """Run prepare commands, raising if one exits non-zero.

        Their output is attributed to sim, or to the simulation as a whole when
        no simulator is given.
        """
        pass


class DetachedCommandExecutorFactory(CommandExecutorFactoryBase):
    """Default for an instantiation that no runtime is executing.

    Messages go to stderr rather than being lost. Commands cannot be run, as
    spawning processes is the runtime's job.
    """

    async def msg_info(self, msg: str) -> None:
        print(msg, file=sys.stderr)

    async def msg_warning(self, msg: str) -> None:
        print(msg, file=sys.stderr)

    async def msg_error(self, msg: str) -> None:
        print(msg, file=sys.stderr)

    async def exec_prepare_cmds(
        self, cmds: list[str], sim: sim_base.Simulator | None = None
    ) -> None:
        raise RuntimeError(
            "cannot execute prepare commands: this instantiation is not executed by a runtime"
        )
