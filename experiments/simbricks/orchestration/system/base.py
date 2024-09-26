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

from __future__ import annotations

import abc
import typing as tp
from simbricks.orchestration.utils import base as util_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base


class System:
    """Defines System configuration of the whole simulation"""

    def __init__(self) -> None:
        self.all_component: list[Component] = []

    def add_component(self, c: Component) -> None:
        assert c.system == self
        self.all_component.append(c)


class Component(util_base.IdObj):

    def __init__(self, s: System) -> None:
        super().__init__()
        self.system = s
        s.parameters = {}
        s.add_component(self)
        self.name: str = ""

    @abc.abstractmethod
    def interfaces(self) -> list[Interface]:
        return []

    @abc.abstractmethod
    def add_if(self, interface: tp.Any) -> None:
        raise Exception("must be overwritten by subclass")

    def channels(self) -> list[Channel]:
        return [i.channel for i in self.interfaces() if i.is_connected()]

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        pass


class Interface(util_base.IdObj):
    def __init__(self, c: Component) -> None:
        super().__init__()
        self.component = c
        self.channel: Channel | None = None

    def is_connected(self) -> bool:
        return self.channel is not None

    def disconnect(self) -> None:
        self.channel = None

    def connect(self, c: Channel) -> None:
        assert self.channel is None
        self.channel = c

    def find_peer(self) -> Interface:
        assert self.channel is not None
        if self.channel.a == self:
            peer_if = self.channel.b
        else:
            peer_if = self.channel.a
        return peer_if

    T = tp.TypeVar("T")

    @staticmethod
    def filter_by_type(interfaces: list[Interface], ty: type[T]) -> list[T]:
        return list(filter(lambda inf: isinstance(inf, ty), interfaces))


class Channel(util_base.IdObj):
    def __init__(self, a: Interface, b: Interface) -> None:
        super().__init__()
        self.latency = 500
        self.a: Interface = a
        self.a.connect(self)
        self.b: Interface = b
        self.b.connect(self)

    def interfaces(self) -> list[Interface]:
        return [self.a, self.b]

    def disconnect(self):
        # Note AK: this is a bit ugly, this leaves the channel dangling. But
        # it's not referenced anywhere, so that's fine I guess.
        self.a.disconnect()
        self.b.disconnect()
