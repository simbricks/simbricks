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
import simbricks.orchestration.instantiation.base as instantiation
from simbricks.orchestration.system import base as base
from simbricks.orchestration.system import eth as eth
from simbricks.orchestration.system import nic as nic
from simbricks.orchestration.system import pcie as pcie
from simbricks.orchestration.system.host import app
from simbricks.utils import base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.system.host import disk_images


class Host(base.Component):
    def __init__(self, s: base.System):
        super().__init__(s)
        self.applications: list[app.Application] = []

    def add_app(self, a: app.Application) -> None:
        self.applications.append(a)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()

        applications_json = []
        for app in self.applications:
            utils_base.has_attribute(app, "toJSON")
            applications_json.append(app.toJSON())
        json_obj["applications"] = applications_json

        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> Host:
        instance = super().fromJSON(system=system, json_obj=json_obj)
        instance.applications = []

        applications_json = utils_base.get_json_attr_top(json_obj, "applications")
        for app_json in applications_json:
            app_class = utils_base.get_cls_by_json(app_json)
            utils_base.has_attribute(app_class, "fromJSON")
            app = app_class.fromJSON(system, app_json)
            instance.add_app(app)

        return instance

    def connect_pcie_dev(self, dev: pcie.PCIeSimpleDevice) -> pcie.PCIeChannel:
        pcie_if = pcie.PCIeHostInterface(self)
        self.add_if(pcie_if)
        pcichannel0 = pcie.PCIeChannel(pcie_if, dev._pci_if)
        return pcichannel0


class FullSystemHost(Host):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.memory: int = 2048
        self.cores: int = 1
        self.cpu_freq: str = "3GHz"
        self.disks: list[disk_images.DiskImage] = []

    def add_disk(self, disk: disk_images.DiskImage) -> None:
        self.disks.append(disk)

    async def prepare(self, inst: instantiation.Instantiation) -> None:
        promises = [disk.prepare(inst) for disk in self.disks]
        await asyncio.gather(*promises)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["memory"] = self.memory
        json_obj["cores"] = self.cores
        json_obj["cpu_freq"] = self.cpu_freq

        disks_json = []
        for disk in self.disks:
            utils_base.has_attribute(disk, "toJSON")
            disks_json.append(disk.toJSON())
        json_obj["disks"] = disks_json

        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> FullSystemHost:
        instance = super().fromJSON(system, json_obj)
        instance.memory = int(utils_base.get_json_attr_top(json_obj, "memory"))
        instance.cores = int(utils_base.get_json_attr_top(json_obj, "cores"))
        instance.cpu_freq = utils_base.get_json_attr_top(json_obj, "cpu_freq")

        instance.disks = []
        disks_json = utils_base.get_json_attr_top(json_obj, "disks")
        for disk_js in disks_json:
            disk_class = utils_base.get_cls_by_json(disk_js)
            utils_base.has_attribute(disk_class, "fromJSON")
            disk = disk_class.fromJSON(system, disk_js)
            instance.add_disk(disk)

        return instance


class BaseLinuxHost(FullSystemHost):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.applications: list[app.BaseLinuxApplication] = []
        self.load_modules = []
        self.kcmd_append: str | None = None

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
        cmds = self._concat_app_cmds(
            inst, app.BaseLinuxApplication.cleanup_cmds.__name__
        )
        sim = inst.find_sim_by_spec(spec=self)
        cleanup = sim.cleanup_commands()
        cmds += cleanup
        return cmds

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
        sim = inst.find_sim_by_spec(spec=self)
        if inst.create_checkpoint:
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

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["load_modules"] = self.load_modules
        json_obj["kcmd_append"] = self.kcmd_append
        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> BaseLinuxHost:
        instance = super().fromJSON(system, json_obj)
        instance.load_modules = utils_base.get_json_attr_top(json_obj, "load_modules")
        instance.kcmd_append = utils_base.get_json_attr_top(json_obj, "kcmd_append")
        return instance


class LinuxHost(BaseLinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers: list[str] = []
        self.hostname: str | None = "ubuntu"

    def cleanup_cmds(self, inst: instantiation.Instantiation) -> list[str]:
        return super().cleanup_cmds(inst) + ["poweroff -f"]

    def prepare_pre_cp(self, inst: instantiation.Instantiation) -> list[str]:
        """Commands to run to prepare node before checkpointing."""
        cmds = [
            "set -x",
            "export HOME=/root",
            "export LANG=en_US",
            'export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:'
            + '/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"',
        ]
        if self.hostname is not None:
            cmds += [
                f"hostname -b {self.hostname}",
                f'echo "127.0.1.1 {self.hostname}\n" >> /etc/hosts',
            ]
        cmds += super().prepare_pre_cp(inst)
        return cmds

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
            if not utils_base.check_types(
                inf.component, eth.EthSimpleNIC, nic.SimplePCIeNIC
            ):
                continue
            # Get ifname parameter if set, otherwise default to ethX
            ifn = f"eth{index}"
            index += 1
            com: eth.EthSimpleNIC | nic.SimplePCIeNIC = inf.component

            # Force MAC if requested TODO: FIXME
            # if "force_mac_addr" in i.parameters:
            #     mac = i.parameters["force_mac_addr"]
            #     l.append(f"ip link set dev {ifn} address " f"{mac}")

            # Bring interface up
            cmds.append(f"ip link set dev {ifn} up")

            # Add IP addresses if included
            assert com._ip is not None
            cmds.append(f"ip addr add {com._ip}/24 dev {ifn}")

        return cmds

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["drivers"] = self.drivers
        json_obj["hostname"] = self.hostname
        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> LinuxHost:
        instance = super().fromJSON(system, json_obj)
        instance.drivers = utils_base.get_json_attr_top(json_obj, "drivers")
        instance.hostname = utils_base.get_json_attr_top(json_obj, "hostname")
        return instance


class I40ELinuxHost(LinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers.append("i40e")


class CorundumLinuxHost(LinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers.append("/tmp/guest/mqnic.ko")

    def config_files(self, inst: instantiation.Instantiation) -> tp.Dict[str, tp.IO]:
        m = {
            "mqnic.ko": open(
                f"{inst.env.repo_base(relative_path='images/mqnic/mqnic.ko')}", "rb"
            )
        }
        return {**m, **super().config_files(inst=inst)}
