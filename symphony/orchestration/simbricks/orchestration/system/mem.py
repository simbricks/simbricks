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

import typing_extensions as tpe

from simbricks.orchestration.system import base
from simbricks.utils import base as utils_base


class MemHostInterface(base.Interface):
    # Note AK: Component here is on purpose. Other simulators than host
    # simulators can also have MemHost interfaces (e.g. a Mem switch)
    def __init__(self, c: base.Component) -> None:
        super().__init__(c)


class MemDeviceInterface(base.Interface):
    def __init__(self, c: base.Component) -> None:
        super().__init__(c)

    def connect(self, c: base.Channel) -> None:
        # Note AK: a bit ugly, but I think we can't get around a rt check here
        if not isinstance(c, MemChannel):
            raise TypeError("MemDeviceInterface only connects to MemChannel")
        super().connect(c)


class MemChannel(base.Channel):
    def __init__(self, host: MemHostInterface, dev: MemDeviceInterface) -> None:
        super().__init__(host, dev)

    def host_if(self) -> MemHostInterface:
        return self.a

    def dev_if(self) -> MemDeviceInterface:
        return self.b


class MemSimpleDevice(base.Component):
    def __init__(self, s: base.System):
        super().__init__(s)
        self._mem_if: MemDeviceInterface = MemDeviceInterface(c=self)
        self.ifs.append(self._mem_if)
        self._addr = 0xE000000000000000
        self._size = 1024 * 1024 * 1024  # 1GB
        self._as_id = 0
        self._load_elf: str | None = None

    def add_if(self, interface: MemDeviceInterface) -> None:
        raise Exception(
            f"you overwrite MemDeviceInterface._mem_if ({self._mem_if.id()} -> {interface.id()}) "
        )

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["mem_if"] = self._mem_if.id()
        json_obj["addr"] = self._addr
        json_obj["size"] = self._size
        json_obj["as_id"] = self._as_id
        json_obj["load_elf"] = self._load_elf
        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        mem_if_id = int(utils_base.get_json_attr_top(json_obj, "mem_if"))
        addr = utils_base.get_json_attr_top(json_obj, "addr")
        size = utils_base.get_json_attr_top(json_obj, "size")
        as_id = utils_base.get_json_attr_top(json_obj, "as_id")
        instance._mem_if = system.get_inf(mem_if_id)
        instance._addr = addr
        instance._size = size
        instance._as_id = as_id
        instance._load_elf = utils_base.get_json_attr_top_or_none(json_obj, "load_elf")
        return instance


class MemInterconnect(base.Component):
    def __init__(self, s: base.System):
        super().__init__(s)
        self._routes: list[dict] = []


    def add_if(self, interface: MemDeviceInterface | MemHostInterface) -> None:
        super().add_if(interface)

    def connect_host(self, peer_if: MemHostInterface) -> MemChannel:
        our_if = MemDeviceInterface(self)
        self.add_if(our_if)
        mc = MemChannel(peer_if, our_if)
        return mc

    def connect_device(self, peer_if: MemDeviceInterface) -> MemChannel:
        our_if = MemHostInterface(self)
        self.add_if(our_if)
        mc = MemChannel(our_if, peer_if)
        return mc

    def add_route(self, dev: MemHostInterface, vaddr: int, len: int, paddr: int = 0):
        assert dev in self.interfaces()
        self._routes.append({
            'dev': dev.id(),
            'vaddr': vaddr,
            'len': len,
            'paddr': paddr,
        })

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["routes"] = self._routes
        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        routes = utils_base.get_json_attr_top(json_obj, "routes")
        instance._routes = routes
        return instance
