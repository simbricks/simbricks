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

import abc
import simbricks.orchestration.experiments as exp
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.simulation import channel as sim_chan
from simbricks.orchestration.experiment import experiment_environment_new as exp_env
from simbricks.orchestration.instantiation import base as inst_base


class Simulator(abc.ABC):
    """Base class for all simulators."""

    def __init__(self, e: exp.Experiment) -> None:
        self.extra_deps: list[Simulator] = []
        self.name = ""
        self.experiment = e
        self._components: set[sys_base.Component] = []

    def resreq_cores(self) -> int:
        """
        Number of cores this simulator requires during execution.

        This is used for scheduling multiple runs and experiments.
        """
        return 1

    def resreq_mem(self) -> int:
        """
        Number of memory in MB this simulator requires during execution.

        This is used for scheduling multiple runs and experiments.
        """
        return 64

    def full_name(self) -> str:
        """Full name of the simulator."""
        return ""

    # pylint: disable=unused-argument
    def prep_cmds(self, env: exp_env.ExpEnv) -> list[str]:
        """Commands to prepare execution of this simulator."""
        return []

    # TODO: call this in subclasses
    def _add_component(self, comp: sys_base.Channel) -> None:
        self._components.add(comp)

    def _chan_needs_instance(self, chan: sys_base.Channel) -> bool:
        if (
            chan.a.component in self._components
            and chan.b.component in self._components
        ):
            return False
        return True

    def _get_sock_path(
        self, inst: inst_base.Instantiation, chan: sys_base.Channel
    ) -> tuple[sim_chan.Channel, inst_base.Socket] | tuple[None, None]:
        if not self._chan_needs_instance(chan):
            return None, None
        channel = self.experiment.retrieve_or_create_channel(chan)
        return channel, inst.get_socket_path(channel)

    # pylint: disable=unused-argument
    @abc.abstractmethod
    def run_cmd(self, env: exp_env.ExpEnv) -> str:
        """Command to execute this simulator."""
        return ""

    def dependencies(self) -> list[Simulator]:
        """Other simulators to execute before this one."""
        return []

    # Sockets to be cleaned up
    # pylint: disable=unused-argument
    def sockets_cleanup(self, env: exp_env.ExpEnv) -> list[str]:
        return []

    # sockets to wait for indicating the simulator is ready
    # pylint: disable=unused-argument
    def sockets_wait(self, env: exp_env.ExpEnv) -> list[str]:
        return []

    def start_delay(self) -> int:
        return 5

    def wait_terminate(self) -> bool:
        return False
