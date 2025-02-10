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

from __future__ import annotations

import abc
import typing

from simbricks.orchestration.instantiation import socket as inst_socket
from simbricks.utils import base as utils_base
from simbricks.utils import file as utils_file

if typing.TYPE_CHECKING:
    import simbricks.orchestration.system.base as sys_base
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.simulation import base as sim_base


class Proxy(utils_base.IdObj, abc.ABC):

    def __init__(self, connection_mode: inst_socket.SockType):
        super().__init__()
        self._interfaces: list[sys_base.Interface]
        """
        The interfaces this proxy handles.
        
        Order is important here because proxies forward messages for SimBricks
        sockets in the order these sockets are passed on the command-line. So
        for two connecting proxies executing on separate runners, this order
        must be the same.
        """
        self._connection_mode: inst_socket.SockType = connection_mode

    @property
    def name(self) -> str:
        return f"proxy_{self.id()}"

    @abc.abstractmethod
    def run_cmd(self) -> str:
        pass

    def sockets_wait(self, inst: inst_base.Instantiation) -> set[inst_socket.Socket]:
        wait_sockets = []
        for iface in self._interfaces:
            socket = inst.update_get_socket(iface)
            if socket.type == inst_socket.SockType.LISTEN:
                wait_sockets.append(socket)
        return wait_sockets

    def _find_opposing_proxy(self, instantiation: inst_base.Instantiation) -> Proxy:
        # TODO (Jonas) Implement this
        pass


class DummyProxy(Proxy):

    def __init__(self) -> None:
        super().__init__()


class TCPProxy(Proxy):

class ProxyPair(utils_base.IdObj):

    def __init__(
        self, instantiation: inst_base.Instantiation, proxy_a: Proxy, proxy_b: Proxy
    ) -> None:
        self._inst: inst_base.Instantiation = instantiation
        self._channels: set[sim_base.Channel] = set()
        self.proxy_a: Proxy = proxy_a
        self.proxy_b: Proxy = proxy_b

    def assign_sim_channel(channel: sim_base.Channel) -> None:
        # TODO (Jonas) Implement this
        pass
