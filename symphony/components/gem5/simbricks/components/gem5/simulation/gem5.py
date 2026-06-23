# Copyright 2026 Max Planck Institute for Software Systems,
# National University of Singapore, and SimBricks UG (haftungsbeschränkt)
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

from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.simulation import host as sim_host
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import host as sys_host
from simbricks.orchestration.system import pcie as sys_pcie
from simbricks.orchestration.system import mem as sys_mem
from simbricks.orchestration.system import disk_images
from simbricks.utils import base as utils_base, file as utils_file
from simbricks.orchestration.instantiation import socket as inst_socket


class Gem5Sim(sim_host.HostSim):

    def __init__(self, simulation: sim_base.Simulation):
        super().__init__(
            simulation=simulation, executable="sims/external/gem5/build/X86/gem5"
        )
        self.name = f"Gem5Sim-{self._id}"
        self.cpu_type_cp = "X86KvmCPU"
        self.cpu_type = "TimingSimpleCPU"
        self.extra_main_args: list[str] = []
        self.extra_config_args: list[str] = []
        self._variant: str = "fast"
        self._sys_clock: str = "1GHz"  # TODO: move to system module

    def supports_checkpointing(self) -> bool:
        return True

    def resreq_cores(self) -> int:
        return 1

    def resreq_mem(self) -> int:
        return 1024

    def supported_image_formats(self) -> list[str]:
        return ["raw"]

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["cpu_type_cp"] = self.cpu_type_cp
        json_obj["cpu_type"] = self.cpu_type
        json_obj["extra_main_args"] = self.extra_main_args
        json_obj["extra_config_args"] = self.extra_config_args
        json_obj["_variant"] = self._variant
        json_obj["_sys_clock"] = self._sys_clock
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(simulation, json_obj)
        instance.cpu_type_cp = utils_base.get_json_attr_top(json_obj, "cpu_type_cp")
        instance.cpu_type = utils_base.get_json_attr_top(json_obj, "cpu_type")
        instance.extra_main_args = utils_base.get_json_attr_top(
            json_obj, "extra_main_args"
        )
        instance.extra_config_args = utils_base.get_json_attr_top(
            json_obj, "extra_config_args"
        )
        instance._variant = utils_base.get_json_attr_top(json_obj, "_variant")
        instance._sys_clock = utils_base.get_json_attr_top(json_obj, "_sys_clock")
        return instance

    async def copy_disk_image(
        self, inst: inst_base.Instantiation, disk_image: disk_images.DiskImage, ident: str
    ):
        return disk_image.path(inst, disk_image.find_format(self))

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        await super().prepare(inst=inst)
        utils_file.mkdir(inst.env.cpdir_sim(sim=self))

    def checkpoint_commands(self) -> list[str]:
        return ["m5 checkpoint"]

    def cleanup_commands(self) -> list[str]:
        return ["m5 exit"]

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cpu_type = self.cpu_type
        if inst.create_checkpoint:
            cpu_type = self.cpu_type_cp

        full_sys_hosts = self.filter_components_by_type(ty=sys_host.BaseLinuxHost)
        if len(full_sys_hosts) != 1:
            raise Exception("Gem5Sim only supports simulating 1 FullSystemHost")
        host_spec = full_sys_hosts[0]

        cmd = f"{inst.env.repo_base(f'{self._executable}.{self._variant}')} --outdir={inst.env.get_simulator_output_dir(sim=self)} "
        cmd += " ".join(self.extra_main_args)
        cmd += (
            f" {inst.env.repo_base('sims/external/gem5/configs/simbricks/simbricks.py')} --caches --l2cache "
            "--l1d_size=32kB --l1i_size=32kB --l2_size=32MB "
            "--l1d_assoc=8 --l1i_assoc=8 --l2_assoc=16 "
            f"--cacheline_size=64 --cpu-clock={host_spec.cpu_freq}"
            f" --sys-clock={self._sys_clock} "
            f"--checkpoint-dir={inst.env.cpdir_sim(sim=self)} "
            f"--kernel={inst.env.repo_base('images/vmlinux')} "
        )

        assert host_spec in self._disk_images
        for disk in self._disk_images[host_spec]:
            cmd += f"--disk-image={disk[1]} "

        cmd += (
            f"--cpu-type={cpu_type} --mem-size={host_spec.memory}MB "
            f"--num-cpus={host_spec.cores} "
            "--mem-type=DDR4_2400_16x4 "
        )

        if host_spec.kcmd_append is not None:
            cmd += f'--command-line-append="{host_spec.kcmd_append}" '

        if inst.create_checkpoint:
            cmd += "--max-checkpoints=1 "

        if inst.restore_checkpoint:
            cmd += "-r 1 "

        if len(self.get_channels()) > 0:
            latency, sync_period, run_sync = (
                sim_base.Simulator.get_unique_latency_period_sync(
                    channels=self.get_channels()
                )
            )

        fsh_interfaces = host_spec.interfaces()

        pci_interfaces = sys_base.Interface.filter_by_type(
            interfaces=fsh_interfaces, ty=sys_pcie.PCIeHostInterface
        )
        for inf in pci_interfaces:
            assert(len(self.get_channels()) > 0)
            socket = inst.get_socket(interface=inf)
            if socket is None:
                continue
            assert socket._type == inst_socket.SockType.CONNECT
            cmd += (
                f"--simbricks-pci=connect:{socket._path}"
                f":latency={latency}ns"
                f":sync_interval={sync_period}ns"
            )
            if run_sync and not inst.create_checkpoint:
                cmd += ":sync"
            cmd += " "

        mem_interfaces = sys_base.Interface.filter_by_type(
            interfaces=fsh_interfaces, ty=sys_mem.MemHostInterface
        )
        for inf in mem_interfaces:
            assert(len(self.get_channels()) > 0)
            socket = inst.get_socket(interface=inf)
            if socket is None:
                continue
            assert socket._type == inst_socket.SockType.CONNECT
            utils_base.has_expected_type(inf.component, sys_mem.MemSimpleDevice)
            dev: sys_mem.MemSimpleDevice = inf.component
            cmd += (
                f"--simbricks-mem={dev._size}@{dev._addr}@{dev._as_id}@"
                f"connect:{socket._path}"
                f":latency={latency}ns"
                f":sync_interval={sync_period}ns"
            )
            if run_sync and not inst.create_checkpoint:
                cmd += ":sync"
            cmd += " "

        # TODO: FIXME
        # for net in self.net_directs:
        #     cmd += (
        #         '--simbricks-eth-e1000=listen'
        #         f':{env.net2host_eth_path(net, self)}'
        #         f':{env.net2host_shm_path(net, self)}'
        #         f':latency={net.eth_latency}ns'
        #         f':sync_interval={net.sync_period}ns'
        #     )
        #     if cpu_type == 'TimingSimpleCPU':
        #         cmd += ':sync'
        #     cmd += ' '

        cmd += " ".join(self.extra_config_args)

        return cmd
