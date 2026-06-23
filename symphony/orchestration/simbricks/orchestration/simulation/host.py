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
import typing_extensions as tpe

from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import host as sys_host
from simbricks.orchestration.system import disk_images
from simbricks.orchestration.instantiation import socket as inst_socket


class HostSim(sim_base.Simulator):

    def __init__(self, simulation: sim_base.Simulation, executable: str, name=""):
        super().__init__(simulation=simulation, executable=executable, name=name)
        self._disk_images: dict[
            sys_host.FullSystemHost, list[tuple[disk_images.DiskImage, str]]
        ] = {}

    def toJSON(self) -> dict:
        return super().toJSON()

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(simulation, json_obj)
        instance._disk_images = {}
        return instance

    def full_name(self) -> str:
        return "host." + self.name

    def add(self, host: sys_host.Host):
        super().add(host)

    @abc.abstractmethod
    def supported_image_formats(self) -> list[str]:
        pass

    @abc.abstractmethod
    async def copy_disk_image(
        self, inst: inst_base.Instantiation, disk_image: disk_images.DiskImage, ident: str
    ) -> str:
        pass

    async def prepare(self, inst: inst_base.Instantiation):
        await super().prepare(inst)

        full_sys_hosts = self.filter_components_by_type(ty=sys_host.FullSystemHost)

        for host in full_sys_hosts:
            host_disks = []
            for i, disk in enumerate(host.disks):
                if disk.needs_copy:
                    copy_path = await self.copy_disk_image(inst, disk, f"{host.id()}.{i}")
                    host_disks.append((disk, copy_path))
                else:
                    host_disks.append((disk, disk.path(inst, disk.find_format(self))))
            self._disk_images[host] = host_disks

    def supported_socket_types(
        self, interface: sys_base.Interface
    ) -> set[inst_socket.SockType]:
        return {inst_socket.SockType.CONNECT}
