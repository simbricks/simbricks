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

import math
import asyncio
import typing as tp
import simbricks.orchestration.simulation.base as sim_base
import simbricks.orchestration.system as system
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.experiment.experiment_environment_new import ExpEnv

if tp.TYPE_CHECKING:
    from simbricks.orchestration.system import host as sys_host

class HostSim(sim_base.Simulator):

    def __init__(self, e: sim_base.Simulation):
        super().__init__(e)
        self.name = f"{self._id}"

    def full_name(self) -> str:
        return "host." + self.name

    def add(self, host: sys_host.Host):
        super().add(host)

    def config_str(self) -> str:
        return []

    def supported_image_formats(self) -> list[str]:
        raise Exception("implement me")


class Gem5Sim(HostSim):

    def __init__(self, e: sim_base.Simulation):
        super().__init__(e)
        self.name = super().full_name()
        self.cpu_type_cp = "X86KvmCPU"
        self.cpu_type = "TimingSimpleCPU"
        self.extra_main_args: list[str] = []
        self.extra_config_args: list[str] = []
        self.variant = "fast"
        self.modify_checkpoint_tick = True
        self.wait = True

    def resreq_cores(self) -> int:
        return 1

    def resreq_mem(self) -> int:
        return 4096
    
    def supported_image_formats(self) -> list[str]:
        return ["raw"]

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        await super().prepare(inst=inst)
        
        prep_cmds = [f'mkdir -p {inst.cpdir_subdir(sim=self)}']
        task = asyncio.create_task(
                inst.executor.run_cmdlist(label="prepare", cmds=prep_cmds, verbose=True)
            )
        await task

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cpu_type = self.cpu_type
        if env.create_cp:
            cpu_type = self.cpu_type_cp

        # TODO
        cmd = f"{env.gem5_path(self.variant)} --outdir={env.gem5_outdir(self)} "
        cmd += " ".join(self.extra_main_args)
        cmd += (
            f" {env.gem5_py_path} --caches --l2cache "
            "--l1d_size=32kB --l1i_size=32kB --l2_size=32MB "
            "--l1d_assoc=8 --l1i_assoc=8 --l2_assoc=16 "
            f"--cacheline_size=64 --cpu-clock={self.hosts[0].cpu_freq}"
            f" --sys-clock={self.hosts[0].sys_clock} "
            f"--checkpoint-dir={env.gem5_cpdir(self)} "
            f"--kernel={env.gem5_kernel_path} "
            f"--disk-image={env.hd_raw_path(self.hosts[0].disk_image)} "
            f"--disk-image={env.cfgtar_path(self)} "
            f"--cpu-type={cpu_type} --mem-size={self.hosts[0].memory}MB "
            f"--num-cpus={self.hosts[0].cores} "
            "--mem-type=DDR4_2400_16x4 "
        )

        for dev in self.hosts[0].ifs:  # TODO
            if dev == dev.channel.a:
                peer_if = dev.channel.b
            else:
                peer_if = dev.channel.a

            peer_sim = self.experiment.find_sim(peer_if)
            chn_sim = self.experiment.find_sim(dev.channel)
            cmd += (
                f"--simbricks-pci=connect:{env.dev_pci_path(peer_sim)}"
                f":latency={dev.channel.latency}ns"
                f":sync_interval={chn_sim.sync_period}ns"
            )
            # if cpu_type == 'TimingSimpleCPU' and: #TODO: FIXME
            #     cmd += ':sync'
            cmd += " "

        return cmd


    def checkpoint_commands(self) -> list[str]:
        return ["m5 checkpoint"]


class QemuSim(HostSim):

    def __init__(self, e: sim_base.Simulation):
        super().__init__(e)

    def resreq_cores(self) -> int:
        if self.sync:
            return 1
        else:
            # change it to sum of all hosts
            return self.hosts[0].cores + 1

    def resreq_mem(self) -> int:
        return 8192

    def supported_image_formats(self) -> list[str]:
        return ["raw", "qcow2"]

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        await super().prepare(inst=inst)

        prep_cmds = []
        full_sys_hosts = tp.cast(
            list[system.FullSystemHost],
            self.filter_components_by_type(ty=system.FullSystemHost),
        )

        prep_cmds = []
        for fsh in full_sys_hosts:
            disks = tp.cast(list[system.DiskImage], fsh.disks)
            for disk in disks:
                prep_cmds.append(
                    f'{inst.qemu_img_path()} create -f qcow2 -o '
                    f'backing_file="{disk.path(inst=inst, format="qcow2")}" '
                    f'{inst.hdcopy_path(img=disk, format="qcow2")}'
                )

        task = asyncio.create_task(
                inst.executor.run_cmdlist(label="prepare", cmds=prep_cmds, verbose=True)
            )
        await task

    def run_cmd(self, env: ExpEnv) -> str:
        accel = ",accel=kvm:tcg" if not self.sync else ""
        if self.hosts[0].disks[0].kcmd_append:
            kcmd_append = " " + self.hosts[0].kcmd_append
        else:
            kcmd_append = ""

        cmd = (
            f"{env.qemu_path} -machine q35{accel} -serial mon:stdio "
            "-cpu Skylake-Server -display none -nic none "
            f"-kernel {env.qemu_kernel_path} "
            f"-drive file={env.hdcopy_path(self)},if=ide,index=0,media=disk "
            f"-drive file={env.cfgtar_path(self)},if=ide,index=1,media=disk,"
            "driver=raw "
            '-append "earlyprintk=ttyS0 console=ttyS0 root=/dev/sda1 '
            f'init=/home/ubuntu/guestinit.sh rw{kcmd_append}" '
            f"-m {self.hosts[0].memory} -smp {self.hosts[0].cores} "
        )

        if self.sync:
            unit = self.hosts[0].cpu_freq[-3:]
            if unit.lower() == "ghz":
                base = 0
            elif unit.lower() == "mhz":
                base = 3
            else:
                raise ValueError("cpu frequency specified in unsupported unit")
            num = float(self.hosts[0].cpu_freq[:-3])
            shift = base - int(math.ceil(math.log(num, 2)))

            cmd += f" -icount shift={shift},sleep=off "

        for dev in self.hosts[0].ifs:
            if dev == dev.channel.a:
                peer_if = dev.channel.b
            else:
                peer_if = dev.channel.a

            peer_sim = self.experiment.find_sim(peer_if)
            chn_sim = self.experiment.find_sim(dev.channel)

            cmd += f"-device simbricks-pci,socket={env.dev_pci_path(peer_sim)}"
            if self.sync:
                cmd += ",sync=on"
                cmd += f",pci-latency={dev.channel.latency}"
                cmd += f",sync-period={chn_sim.sync_period}"
                # if self.sync_drift is not None:
                #     cmd += f',sync-drift={self.sync_drift}'
                # if self.sync_offset is not None:
                #     cmd += f',sync-offset={self.sync_offset}'
            else:
                cmd += ",sync=off"
            cmd += " "

        return cmd
