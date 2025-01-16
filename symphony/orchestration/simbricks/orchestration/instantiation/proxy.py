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

import typing

import simbricks.utils.base as util_base
from simbricks.orchestration.instantiation import socket as inst_socket
import abc
import typing

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base
    import simbricks.orchestration.system.base as sys_base


class Proxy(util_base.IdObj, abc.ABC):

    def __init__(self):
        super().__init__()
        self._interfaces: list[sys_base.Interface]
        """
        The interfaces this proxy provides.
        
        Order is important here because proxies forward messages for SimBricks
        sockets in the order these sockets are passed on the command-line. So
        for two connecting proxies executing on separate runners, this order
        must be the same.
        """
        self.connection_mode: inst_socket.SockType = inst_socket.SockType.CONNECT

    @property
    def name(self) -> str:
        return f"proxy_{self.id()}"

    @abc.abstractmethod
    def run_cmd() -> str:
        pass

    def sockets_wait(self, inst: inst_base.Instantiation) -> set[inst_socket.Socket]:
        wait_sockets = []
        for iface in self._interfaces:
            socket = inst.update_get_socket(iface)
            if socket.type == inst_socket.SockType.LISTEN:
                wait_sockets.append(socket)
        return wait_sockets

    def supported_socket_types(
        interface: sys_base.Interface,
    ) -> set[inst_socket.SockType]:
        return {inst_socket.SockType.CONNECT, inst_socket.SockType.LISTEN}


class DummyProxy(Proxy):

    def __init__(self):
        super().__init__()


class TCPProxy(Proxy):

    def __init__(self):
        super().__init__()
        self.ip: str
        self.port: int


class RDMAProxy(Proxy):

    def __init__(self):
        super().__init__()
        self.ip: str
        self.port: int
