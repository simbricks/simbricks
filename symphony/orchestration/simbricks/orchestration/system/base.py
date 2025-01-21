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

import typing as tp
from simbricks.utils import base as util_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base


class System(util_base.IdObj):
    """Defines System configuration of the whole simulation"""

    def __init__(self) -> None:
        super().__init__()
        self._all_components: dict[int, Component] = {}
        self._all_interfaces: dict[int, Interface] = {}
        self._all_channels: dict[int, Channel] = {}

    def _add_component(self, c: Component) -> None:
        assert c.system == self
        assert c.id() not in self._all_components
        self._all_components[c.id()] = c

    def get_comp(self, ident: int) -> Component:
        if ident not in self._all_components:
            raise Exception(f"system object does not store component with id {ident}")

        return self._all_components[ident]

    def _add_interface(self, i: Interface) -> None:
        assert i.component.id() in self._all_components
        assert i.id() not in self._all_interfaces
        self._all_interfaces[i.id()] = i

    def get_inf(self, ident: int) -> Interface:
        if ident not in self._all_interfaces:
            raise Exception(f"system object does not store interface with id {ident}")

        return self._all_interfaces[ident]

    def _add_channel(self, c: Channel) -> None:
        assert c.a.id() in self._all_interfaces and c.b.id() in self._all_interfaces
        assert c.id() not in self._all_channels
        self._all_channels[c.id()] = c

    def get_chan(self, ident: int) -> Channel:
        if ident not in self._all_channels:
            raise Exception(f"system does not store channel with id {ident}")

        return self._all_channels[ident]

    @staticmethod
    def set_latencies(channels: list[Channel], amount: int, ratio: util_base.Time) -> None:
        for chan in channels:
            chan.set_latency(amount, ratio)

    def latencies(self, amount: int, ratio: util_base.Time, channel_type: tp.Any) -> None:
        relevant_channels = list(
            filter(
                lambda chan: util_base.check_type(chan, channel_type),
                self._all_channels.values(),
            )
        )
        System.set_latencies(relevant_channels, amount, ratio)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()

        components_json = []
        for _, comp in self._all_components.items():
            util_base.has_attribute(comp, "toJSON")
            comp_json = comp.toJSON()
            components_json.append(comp_json)

        json_obj["all_components"] = components_json

        channels_json = []
        for _, chan in self._all_channels.items():
            util_base.has_attribute(chan, "toJSON")
            channels_json.append(chan.toJSON())

        json_obj["channels"] = channels_json

        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict) -> System:
        instance = super().fromJSON(json_obj)
        instance._all_components = {}
        instance._all_interfaces = {}
        instance._all_channels = {}

        components_json = util_base.get_json_attr_top(json_obj, "all_components")
        for comp_json in components_json:
            comp_class = util_base.get_cls_by_json(comp_json)
            util_base.has_attribute(comp_class, "fromJSON")
            comp = comp_class.fromJSON(instance, comp_json)

        channels_json = util_base.get_json_attr_top(json_obj, "channels")
        for chan_json in channels_json:
            chan_class = util_base.get_cls_by_json(chan_json)
            util_base.has_attribute(chan_class, "fromJSON")
            chan = chan_class.fromJSON(instance, chan_json)

        return instance


class Component(util_base.IdObj):

    def __init__(self, s: System) -> None:
        super().__init__()
        self.system = s
        self.ifs: list[Interface] = []
        self.parameters: dict[tp.Any, tp.Any] = {}
        s._add_component(self)
        self.name: str | None = None

    def interfaces(self) -> list[Interface]:
        return self.ifs

    # NOTE: overwrite and call in subclasses
    def add_if(self, interface: Interface) -> None:
        self.ifs.append(interface)

    def channels(self) -> list[Channel]:
        return [i.channel for i in self.interfaces() if i.is_connected()]

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        pass

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["system"] = self.system.id()
        json_obj["name"] = self.name
        json_obj["parameters"] = util_base.dict_to_json(self.parameters)

        interfaces_json = []
        for inf in self.interfaces():
            util_base.has_attribute(inf, "toJSON")
            interfaces_json.append(inf.toJSON())
        json_obj["interfaces"] = interfaces_json

        return json_obj

    @classmethod
    def fromJSON(cls, system: System, json_obj: dict) -> Component:
        instance = super().fromJSON(json_obj)
        instance.name = util_base.get_json_attr_top_or_none(json_obj, "name")
        instance.parameters = util_base.json_to_dict(
            util_base.get_json_attr_top(json_obj, "parameters")
        )
        instance.system = system
        system._add_component(instance)

        instance.ifs = []
        interfaces_json = util_base.get_json_attr_top(json_obj, "interfaces")
        for inf_json in interfaces_json:
            inf_class = util_base.get_cls_by_json(inf_json)
            util_base.has_attribute(inf_class, "fromJSON")
            # NOTE: this will add the interface to the system map for retrieval in sub-classes
            inf = inf_class.fromJSON(system, inf_json)

        return instance


class Interface(util_base.IdObj):
    def __init__(self, c: Component) -> None:
        super().__init__()
        self.component = c
        c.system._add_interface(self)
        self.channel: Channel | None = None

    def is_connected(self) -> bool:
        return self.channel is not None

    def disconnect(self) -> None:
        self.channel = None

    def connect(self, c: Channel) -> None:
        if self.channel is not None:
            raise Exception(
                f"cannot connect interface {self.id()} to channel {c.id()}. interface is already connected to channel {self.channel.id()}"
            )
        self.channel = c

    def find_peer(self) -> Interface:
        assert self.channel is not None
        if self.channel.a == self:
            peer_if = self.channel.b
        else:
            peer_if = self.channel.a
        return peer_if

    def get_chan_raise(self) -> Channel:
        if not self.is_connected():
            raise Exception(f"interface(id={self._id}) is not connected to channel")
        return self.channel

    def get_opposing_interface(self) -> Interface:
        chan = self.get_chan_raise()
        return chan.get_opposing_interface(interface=self)

    T = tp.TypeVar("T")

    @staticmethod
    def filter_by_type(interfaces: list[Interface], ty: type[T]) -> list[T]:
        return list(filter(lambda inf: isinstance(inf, ty), interfaces))

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["component"] = self.component.id()
        json_obj["channel"] = self.channel.id()
        return json_obj

    @classmethod
    def fromJSON(cls, system: System, json_obj: dict) -> Interface:
        instance = super().fromJSON(json_obj)
        comp_id = util_base.get_json_attr_top(json_obj, "component")
        comp = system.get_comp(comp_id)
        instance.component = comp
        comp.add_if(instance)
        system._add_interface(instance)
        instance.channel = None
        return instance


class Channel(util_base.IdObj):
    def __init__(self, a: Interface, b: Interface) -> None:
        super().__init__()
        self.latency = 500  # nanoseconds
        self.a: Interface = a
        self.a.connect(self)
        self.b: Interface = b
        self.b.connect(self)
        self.parameters: dict[tp.Any, tp.Any] = {}
        a.component.system._add_channel(self)

    def interfaces(self) -> list[Interface]:
        return [self.a, self.b]

    def disconnect(self):
        # Note AK: this is a bit ugly, this leaves the channel dangling. But
        # it's not referenced anywhere, so that's fine I guess.
        self.a.disconnect()
        self.b.disconnect()

    def get_opposing_interface(self, interface: Interface) -> Interface:
        if interface is not self.a and interface is not self.b:
            raise Exception(
                "cannot determine opposing interface, interface is not connected to channel"
            )
        opposing = self.a if interface is self.b else self.b
        assert opposing != interface
        return opposing

    def set_latency(self, amount: int, ratio: util_base.Time = util_base.Time.Nanoseconds) -> None:
        util_base.has_expected_type(obj=ratio, expected_type=util_base.Time)
        self.latency = amount * ratio

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["latency"] = self.latency
        json_obj["interface_a"] = self.a.id()
        json_obj["interface_b"] = self.b.id()
        json_obj["parameters"] = util_base.dict_to_json(self.parameters)
        return json_obj

    @classmethod
    def fromJSON(cls, system: System, json_obj: dict) -> Channel:
        instance = super().fromJSON(json_obj)
        instance.latency = int(util_base.get_json_attr_top(json_obj, "latency"))
        instance.parameters = util_base.json_to_dict(
            util_base.get_json_attr_top(json_obj, "parameters")
        )

        inf_id_a = int(util_base.get_json_attr_top(json_obj, "interface_a"))
        inf_id_b = int(util_base.get_json_attr_top(json_obj, "interface_b"))
        inf_a = system.get_inf(ident=inf_id_a)
        inf_b = system.get_inf(ident=inf_id_b)
        instance.a = inf_a
        instance.a.connect(instance)
        instance.b = inf_b
        instance.b.connect(instance)

        system._add_channel(instance)

        return instance
