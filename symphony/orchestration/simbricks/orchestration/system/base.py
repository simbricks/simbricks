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

import uuid
import typing as tp
from simbricks.orchestration.system import disk_images
from simbricks.utils import base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base


class System(utils_base.IdObj):
    """Defines System configuration of the whole simulation"""

    def __init__(self, name: str = str(uuid.uuid4())) -> None:
        super().__init__()
        self.name: str = name
        self._all_components: dict[int, Component] = {}
        self._all_interfaces: dict[int, Interface] = {}
        self._all_channels: dict[int, Channel] = {}
        self._all_disk_images: dict[int, disk_images.DiskImage] = {}
        self._parameters: dict[tp.Any, tp.Any] = {}

    def _add_component(self, c: Component) -> None:
        assert c.system == self
        assert c.id() not in self._all_components
        self._all_components[c.id()] = c

    def get_comp(self, ident: int) -> Component:
        if ident not in self._all_components:
            raise Exception(f"system object does not store component with id {ident}")

        return self._all_components[ident]

    def _add_interface(self, i: Interface) -> None:
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

    def _add_disk_image(self, disk_image: disk_images.DiskImage) -> None:
        assert disk_image.id() not in self._all_disk_images
        self._all_disk_images[disk_image.id()] = disk_image

    def _get_disk_image(self, ident: int) -> disk_images.DiskImage:
        if ident not in self._all_disk_images:
            raise Exception(f"system does not store disk image with id {ident}")

        return self._all_disk_images[ident]

    @staticmethod
    def set_latencies(channels: list[Channel], amount: int, ratio: utils_base.Time) -> None:
        for chan in channels:
            chan.set_latency(amount, ratio)

    def latencies(
        self, amount: int, ratio: utils_base.Time, channel_type: tp.Any | None = None
    ) -> None:
        relevant_channels = self._all_channels
        if channel_type:
            relevant_channels = list(
                filter(
                    lambda chan: utils_base.check_type(chan, channel_type),
                    self._all_channels.values(),
                )
            )
        System.set_latencies(relevant_channels, amount, ratio)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()

        json_obj["name"] = self.name

        components_json = []
        for _, comp in self._all_components.items():
            utils_base.has_attribute(comp, "toJSON")
            comp_json = comp.toJSON()
            components_json.append(comp_json)

        json_obj["all_components"] = components_json

        interfaces_json = []
        for _, interface in self._all_interfaces.items():
            utils_base.has_attribute(interface, "toJSON")
            inf_json = interface.toJSON()
            interfaces_json.append(inf_json)

        json_obj["interfaces"] = interfaces_json

        channels_json = []
        for _, chan in self._all_channels.items():
            utils_base.has_attribute(chan, "toJSON")
            channels_json.append(chan.toJSON())

        json_obj["channels"] = channels_json

        disk_images_json = []
        for disk_image in self._all_disk_images.values():
            disk_images_json.append(disk_image.toJSON())

        json_obj["disk_images"] = disk_images_json

        json_obj["parameters"] = utils_base.dict_to_json(self._parameters)

        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict, enforce_dummies: bool = False) -> System:
        instance = super().fromJSON(json_obj)
        instance.name = utils_base.get_json_attr_top(json_obj, "name")
        instance._all_components = {}
        instance._all_interfaces = {}
        instance._all_channels = {}
        instance._all_disk_images = {}

        disk_images_json = utils_base.get_json_attr_top(json_obj, "disk_images")
        for disk_image_json in disk_images_json:
            disk_image_class = utils_base.get_cls_by_json(disk_image_json, False)

            if enforce_dummies or disk_image_class is None:
                _ = disk_images.DummyDiskImage.fromJSON(instance, disk_image_json)
                continue

            utils_base.has_attribute(disk_image_class, "fromJSON")
            _ = disk_image_class.fromJSON(instance, disk_image_json)

        interfaces_json = utils_base.get_json_attr_top(json_obj, "interfaces")
        for inf_json in interfaces_json:
            inf_class = utils_base.get_cls_by_json(inf_json, False)

            # create a dummy interface if we cannot deserialize the given
            if enforce_dummies or inf_class is None:
                _ = DummyInterface.fromJSON(instance, inf_json)
                continue

            utils_base.has_attribute(inf_class, "fromJSON")
            _ = inf_class.fromJSON(instance, inf_json)

        components_json = utils_base.get_json_attr_top(json_obj, "all_components")
        for comp_json in components_json:
            comp_class = utils_base.get_cls_by_json(comp_json, False)

            # create a dummy component if we cannot deserialize the given
            if enforce_dummies or comp_class is None:
                _ = DummyComponent.fromJSON(instance, comp_json)
                continue

            utils_base.has_attribute(comp_class, "fromJSON")
            _ = comp_class.fromJSON(instance, comp_json)

        channels_json = utils_base.get_json_attr_top(json_obj, "channels")
        for chan_json in channels_json:
            chan_class = utils_base.get_cls_by_json(chan_json)
            utils_base.has_attribute(chan_class, "fromJSON")
            _ = chan_class.fromJSON(instance, chan_json)

        instance._parameters = utils_base.json_to_dict(
            utils_base.get_json_attr_top(json_obj, "parameters")
        )

        return instance


class Component(utils_base.IdObj):
    """
    Defines a component that is a part of the System Configuration.

    Components could e.g. be hosts, NICs, switches.
    """

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
        json_obj["parameters"] = utils_base.dict_to_json(self.parameters)

        interfaces_json = []
        for inf in self.interfaces():
            interfaces_json.append(inf.id())
            # utils_base.has_attribute(inf, "toJSON")
            # interfaces_json.append(inf.toJSON())
        json_obj["interfaces"] = interfaces_json

        return json_obj

    @classmethod
    def fromJSON(cls, system: System, json_obj: dict) -> Component:
        instance = super().fromJSON(json_obj)
        instance.name = utils_base.get_json_attr_top_or_none(json_obj, "name")
        instance.parameters = utils_base.json_to_dict(
            utils_base.get_json_attr_top(json_obj, "parameters")
        )
        instance.system = system
        system._add_component(instance)

        instance.ifs = []
        interfaces_json = utils_base.get_json_attr_top(json_obj, "interfaces")
        for inf_json in interfaces_json:
            inf_id = int(inf_json)
            inf = system.get_inf(inf_id)
            assert inf.component is None
            instance.add_if(inf)
            inf.component = instance

            # inf_class = utils_base.get_cls_by_json(inf_json)
            # utils_base.has_attribute(inf_class, "fromJSON")
            # # NOTE: this will add the interface to the system map for retrieval in sub-classes
            # inf_class.fromJSON(system, inf_json)

        return instance


class DummyComponent(Component):
    def __init__(self, s: System) -> None:
        super().__init__(s)

    @classmethod
    def fromJSON(cls, system: System, json_obj: dict) -> DummyComponent:
        instance = super().fromJSON(system, json_obj)
        instance._is_dummy = True
        return instance


class Interface(utils_base.IdObj):
    """
    Specifies a single Interface of a Component.

    A host component could e.g. have multiple PCI Interfaces.
    """

    def __init__(self, c: Component) -> None:
        super().__init__()
        self.component: Component | None = c
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
        """
        Deserializes an Interface from its JSON representation.

        Note: This function will not set the component which is done by the component base classes 'fromJSON' method.
        """
        instance = super().fromJSON(json_obj)

        # comp_id = utils_base.get_json_attr_top(json_obj, "component")
        # comp = system.get_comp(comp_id)
        # instance.component = comp
        # comp.add_if(instance)

        system._add_interface(instance)
        instance.channel = None
        instance.component = None

        return instance


class DummyInterface(Interface):

    def __init__(self, c: Component) -> None:
        super().__init__(c)

    @classmethod
    def fromJSON(cls, system: System, json_obj: dict) -> DummyInterface:
        instance = super().fromJSON(system, json_obj)
        instance._is_dummy = True
        return instance


class Channel(utils_base.IdObj):
    def __init__(self, a: Interface, b: Interface) -> None:
        super().__init__()
        self.latency = 500  # nanoseconds
        self.a: Interface = a
        self.a.connect(self)
        self.b: Interface = b
        self.b.connect(self)
        self.parameters: dict[tp.Any, tp.Any] = {}
        a.component.system._add_channel(self)

    def interfaces(self) -> tuple[Interface, Interface]:
        return self.a, self.b

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

    def set_latency(
        self, amount: int, ratio: utils_base.Time = utils_base.Time.Nanoseconds
    ) -> None:
        utils_base.has_expected_type(obj=ratio, expected_type=utils_base.Time)
        self.latency = amount * ratio

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["latency"] = self.latency
        json_obj["interface_a"] = self.a.id()
        json_obj["interface_b"] = self.b.id()
        json_obj["parameters"] = utils_base.dict_to_json(self.parameters)
        return json_obj

    @classmethod
    def fromJSON(cls, system: System, json_obj: dict) -> Channel:
        instance = super().fromJSON(json_obj)
        instance.latency = int(utils_base.get_json_attr_top(json_obj, "latency"))
        instance.parameters = utils_base.json_to_dict(
            utils_base.get_json_attr_top(json_obj, "parameters")
        )

        inf_id_a = int(utils_base.get_json_attr_top(json_obj, "interface_a"))
        inf_id_b = int(utils_base.get_json_attr_top(json_obj, "interface_b"))
        inf_a = system.get_inf(ident=inf_id_a)
        inf_b = system.get_inf(ident=inf_id_b)
        instance.a = inf_a
        instance.a.connect(instance)
        instance.b = inf_b
        instance.b.connect(instance)

        system._add_channel(instance)

        return instance
