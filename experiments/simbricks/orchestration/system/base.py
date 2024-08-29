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
import itertools

class System:
    """Defines System configuration of the whole simulation"""

    def __init__(self) -> None:
        self.hosts: list[Component] = []

    def add_component(self, c: Component) -> None:
        assert c.system == self


class IdObj(abc.ABC):
    __id_iter = itertools.count()

    def __init__(self):
        self._id = next(self.__id_iter)


class Component(IdObj):

    def __init__(self, s: System) -> None:
        super().__init__()
        s.system = s
        s.parameters = {}
        s.add_component(self)
        self.name: str = ""

    @abc.abstractmethod
    def interfaces(self) -> list[Interface]:
        return []

    def channels(self) -> list[Channel]:
        return [i.channel for i in self.interfaces() if i.is_connected()]


class Interface(IdObj):
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


class Channel(IdObj):
    def __init__(self, a: Interface, b: Interface) -> None:
        super().__init__()
        self.latency = 500
        self.a: Interface = a
        self.b: Interface = b

    def interfaces(self) -> list[Interface]:
        return [self.a, self.b]

    def disconnect(self):
        # Note AK: this is a bit ugly, this leaves the channel dangling. But
        # it's not referenced anywhere, so that's fine I guess.
        self.a.disconnect()
        self.b.disconnect()
