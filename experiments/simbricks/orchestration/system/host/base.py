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
import io
import asyncio
from os import path
import simbricks.orchestration.instantiation.base as instantiation
from simbricks.orchestration.system import base as base
from simbricks.orchestration.system import eth as eth
from simbricks.orchestration.system import pcie as pcie
from simbricks.orchestration.system.host import app
from simbricks.orchestration.utils import base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.system.host import disk_images


class Host(base.Component):
    def __init__(self, s: base.System):
        super().__init__(s)
        self.ifs: list[base.Interface] = []
        self.applications: list[app.Application]

    def interfaces(self) -> list[base.Interface]:
        return self.ifs

    def add_if(self, interface: base.Interface) -> None:
        self.ifs.append(interface)

    def add_app(self, a: app.Application) -> None:
        self.applications.append(a)


class FullSystemHost(Host):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.memory = 512
        self.cores = 1
        self.cpu_freq = "3GHz"
        self.disks: list[disk_images.DiskImage] = []

    def add_disk(self, disk: disk_images.DiskImage) -> None:
        self.disks.append(disk)

    async def prepare(self, inst: instantiation.Instantiation) -> None:
        promises = [disk.prepare(inst) for disk in self.disks]
        await asyncio.gather(*promises)


class BaseLinuxHost(FullSystemHost):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.applications: list[app.BaseLinuxApplication] = []
        self.load_modules = []
        self.kcmd_append = ""

    def add_app(self, a: app.BaseLinuxApplication) -> None:
        self.applications.append(a)

    def _concat_app_cmds(
        self,
        inst: instantiation.Instantiation,
        mapper_name: str,
    ) -> list[str]:
        """
        Generate command list from applications by applying `mapper` to each
        application on this host and concatenating the commands.
        """
        cmds = []
        for app in self.applications:
            mapper = getattr(app, mapper_name, None)
            if mapper is None:
                raise Exception(
                    f"coulkd not determine mapper function with name {mapper_name}"
                )
            cmds += mapper(inst)

        return cmds

    def run_cmds(self, inst: instantiation.Instantiation) -> list[str]:
        """Commands to run on node."""
        return self._concat_app_cmds(inst, app.BaseLinuxApplication.run_cmds.__name__)

    def cleanup_cmds(self, inst: instantiation.Instantiation) -> list[str]:
        """Commands to run to cleanup node."""
        return self._concat_app_cmds(
            inst, app.BaseLinuxApplication.cleanup_cmds.__name__
        )

    def config_files(self, inst: instantiation.Instantiation) -> dict[str, tp.IO]:
        """
        Additional files to put inside the node, which are mounted under
        `/tmp/guest/`.

        Specified in the following format: `filename_inside_node`:
        `IO_handle_of_file`
        """
        cfg_files = {}
        for app in self.applications:
            cfg_files |= app.config_files(inst)
        return cfg_files

    def prepare_pre_cp(self, inst: instantiation.Instantiation) -> list[str]:
        """Commands to run to prepare node before checkpointing."""
        return self._concat_app_cmds(
            inst, app.BaseLinuxApplication.prepare_pre_cp.__name__
        )

    def prepare_post_cp(self, inst: instantiation.Instantiation) -> list[str]:
        """Commands to run to prepare node after checkpoint restore."""
        return self._concat_app_cmds(
            inst, app.BaseLinuxApplication.prepare_post_cp.__name__
        )

    def config_str(self, inst: instantiation.Instantiation) -> str:
        if inst.create_cp():
            sim = inst.find_sim_by_spec(spec=self)
            cp_cmd = sim.checkpoint_commands()
        else:
            cp_cmd = []

        es = (
            self.prepare_pre_cp(inst)
            + self.applications[0].prepare_pre_cp(inst)
            + cp_cmd
            + self.prepare_post_cp(inst)
            + self.applications[0].prepare_post_cp(inst)
            + self.run_cmds(inst)
            + self.cleanup_cmds(inst)
        )
        cmd = "\n".join(es)
        return cmd

    def strfile(self, s: str) -> io.BytesIO:
        """
        Helper function to convert a string to an IO handle for usage in
        `config_files()`.

        Using this, you can create a file with the string as its content on the
        simulated node.
        """
        return io.BytesIO(bytes(s, encoding="UTF-8"))


class LinuxHost(BaseLinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers: list[str] = []

    def cleanup_cmds(self, inst: instantiation.Instantiation) -> list[str]:
        return super().cleanup_cmds(inst) + ["poweroff -f"]

    def prepare_pre_cp(self, inst: instantiation.Instantiation) -> list[str]:
        """Commands to run to prepare node before checkpointing."""
        return [
            "set -x",
            "export HOME=/root",
            "export LANG=en_US",
            'export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:'
            + '/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"',
        ] + super().prepare_pre_cp(inst)

    def prepare_post_cp(self, inst) -> list[str]:
        cmds = super().prepare_post_cp(inst)
        for d in self.drivers:
            if d[0] == "/":
                cmds.append(f"insmod {d}")
            else:
                cmds.append(f"modprobe {d}")

        index = 0
        for host_inf in base.Interface.filter_by_type(
            self.interfaces(), pcie.PCIeHostInterface
        ):
            if not host_inf.is_connected():
                continue

            inf = host_inf.get_opposing_interface()
            if not utils_base.check_type(inf.component, eth.EthSimpleNIC):
                continue
            # Get ifname parameter if set, otherwise default to ethX
            ifn = f"eth{index}"
            index += 1
            com: eth.EthSimpleNIC = inf.component

            # Force MAC if requested TODO: FIXME
            # if "force_mac_addr" in i.parameters:
            #     mac = i.parameters["force_mac_addr"]
            #     l.append(f"ip link set dev {ifn} address " f"{mac}")

            # Bring interface up
            cmds.append(f"ip link set dev {ifn} up")

            # Add IP addresses if included
            assert com._ip is not None
            cmds.append(f"ip addr add {com._ip} dev {ifn}")

        return cmds


class I40ELinuxHost(LinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers.append("i40e")


class CorundumLinuxHost(LinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers.append("/tmp/guest/mqnic.ko")

    def config_files(self, inst: instantiation.Instantiation) -> tp.Dict[str, tp.IO]:
        m = {"mqnic.ko": open("../images/mqnic/mqnic.ko", "rb")}
        return {**m, **super().config_files()}
