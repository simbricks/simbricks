# Copyright 2025 Max Planck Institute for Software Systems, and
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

from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import mem as sys_mem
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.instantiation import socket as inst_socket
from simbricks.orchestration.simulation import base as sim_base
from simbricks.utils import base as utils_base


class BasicMem(sim_base.Simulator):

    def __init__(self, simulation: sim_base.Simulation) -> None:
        super().__init__(
            simulation=simulation, executable="sims/mem/basicmem/basicmem", name=""
        )
        self.name = f"basicmem-{self._id}"

    def supported_socket_types(self, interface: sys_base.Interface) -> set[inst_socket.SockType]:
        return {inst_socket.SockType.LISTEN}

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        return super().fromJSON(simulation, json_obj)

    def add(self, mem: sys_mem.MemSimpleDevice):
        utils_base.has_expected_type(mem, sys_mem.MemSimpleDevice)
        super().add(mem)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = f"{inst.env.repo_base(relative_path=self._executable)} "

        mem_devices = self.filter_components_by_type(ty=sys_mem.MemSimpleDevice)
        assert len(mem_devices) == 1
        mem_dev = mem_devices[0]
        socket = inst.get_socket(interface=mem_dev._mem_if)
        assert socket is not None
        shm = inst.env.get_simulator_shm_pool_path(self)
        mem_channels = sim_base.Simulator.filter_channels_by_sys_type(
            self.get_channels(), sys_mem.MemChannel
        )
        mem_latency, mem_sync_period, mem_run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(mem_channels)
        )
        cmd += (
            f" {mem_dev._size} {mem_dev._addr} {mem_dev._as_id} {socket._path}"
            f" {shm} {1 if mem_run_sync else 0} 0 {mem_sync_period} {mem_latency}"
        )
        if mem_dev._load_elf is not None:
            cmd += f" {mem_dev._load_elf}"

        return cmd

class BasicInterconnect(sim_base.Simulator):
    def __init__(self, simulation: sim_base.Simulation) -> None:
        super().__init__(
            simulation=simulation, executable="sims/mem/interconnect/interconnect", name=""
        )
        self.name = f"interconnect-{self._id}"

    def supported_socket_types(self, interface: sys_base.Interface) -> set[inst_socket.SockType]:
        return {inst_socket.SockType.LISTEN, inst_socket.SockType.CONNECT}

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        return super().fromJSON(simulation, json_obj)

    def add(self, ic: sys_mem.MemInterconnect):
        utils_base.has_expected_type(ic, sys_mem.MemInterconnect)
        super().add(ic)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = f"{inst.env.repo_base(relative_path=self._executable)} "

        interconnects = self.filter_components_by_type(ty=sys_mem.MemInterconnect)
        assert len(interconnects) == 1
        ic = interconnects[0]

        shm = inst.env.get_simulator_shm_pool_path(self)
        cmd += f"-p {shm} "

        for intf in ic.interfaces():
            socket = inst.get_socket(interface=intf)
            chan = self._get_channel(intf.channel)
            assert chan is not None
            params_url = self.get_parameters_url(
                inst, socket, sync=chan._synchronized, latency=intf.channel.latency, sync_period=chan.sync_period
            )

            if isinstance(intf, sys_mem.MemHostInterface):
                cmd += f"-d {intf.id()}={params_url} "
            elif isinstance(intf, sys_mem.MemDeviceInterface):
                cmd += f"-h {params_url} "

        for r in ic._routes:
            cmd += f"-m {r['vaddr']},{r['vaddr'] + r['len']},{r['paddr']},{r['dev']} "
        return cmd


class MemTerminal(sim_base.Simulator):

    def __init__(self, simulation: sim_base.Simulation) -> None:
        super().__init__(
            simulation=simulation, executable="sims/mem/terminal/terminal", name=""
        )
        self.name = f"terminal-{self._id}"

    def supported_socket_types(self, interface: sys_base.Interface) -> set[inst_socket.SockType]:
        return {inst_socket.SockType.LISTEN}

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        return super().fromJSON(simulation, json_obj)

    def add(self, mem: sys_mem.MemTerminal):
        utils_base.has_expected_type(mem, sys_mem.MemTerminal)
        super().add(mem)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        assert len(self.components()) == 1
        mem_devices = self.filter_components_by_type(ty=sys_mem.MemTerminal)
        mem_dev = mem_devices[0]

        url = self.get_interface_url(inst, mem_dev._mem_if)
        cmd = f"{inst.env.repo_base(relative_path=self._executable)} {url}"
        return cmd