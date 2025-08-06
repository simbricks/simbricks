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

import tarfile
import typing as tp
import typing_extensions as tpe
import io
import asyncio
from simbricks.orchestration import system
from simbricks.orchestration.system import base as base
from simbricks.orchestration.system import eth as eth
from simbricks.orchestration.system import nic as nic
from simbricks.orchestration.system import pcie as pcie
from simbricks.orchestration.system.host import app
from simbricks.utils import base as utils_base

if tp.TYPE_CHECKING:
    import simbricks.orchestration.instantiation.base as instantiation
    from simbricks.orchestration.system import disk_images


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
            utils_base.has_attribute(app, 'toJSON')
            applications_json.append(app.toJSON())
        json_obj['applications'] = applications_json

        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system=system, json_obj=json_obj)
        instance.applications = []

        applications_json = utils_base.get_json_attr_top(json_obj, "applications")
        for app_json in applications_json:
            app_class = utils_base.get_cls_by_json(app_json)
            utils_base.has_attribute(app_class, "fromJSON")
            app: app.Application = app_class.fromJSON(system, app_json)
            app.host = instance
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
        self.cpu_freq: str = '3GHz'
        self.disks: list[disk_images.DiskImage] = []

    def add_disk(self, disk: disk_images.DiskImage) -> None:
        self.disks.append(disk)

    async def prepare(self, inst: instantiation.Instantiation) -> None:
        promises = [disk.prepare(inst, self) for disk in self.disks]
        await asyncio.gather(*promises)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj['memory'] = self.memory
        json_obj['cores'] = self.cores
        json_obj['cpu_freq'] = self.cpu_freq

        json_obj['disks'] = list(map(lambda disk: disk.id(), self.disks))

        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        instance.memory = int(utils_base.get_json_attr_top(json_obj, 'memory'))
        instance.cores = int(utils_base.get_json_attr_top(json_obj, 'cores'))
        instance.cpu_freq = utils_base.get_json_attr_top(json_obj, 'cpu_freq')

        instance.disks = []
        disk_ids = utils_base.get_json_attr_top(json_obj, 'disks')
        for disk_id in disk_ids:
            disk = system._get_disk_image(disk_id)
            disk.add_host(instance)
            instance.disks.append(disk)

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
        """Generate command list from applications by applying `mapper` to each application on this
        host and concatenating the commands."""
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
        Additional files to put inside the node, which are mounted under `/tmp/guest/`.

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
        cmd = '\n'.join(es)
        return cmd

    def strfile(self, s: str) -> io.BytesIO:
        """
        Helper function to convert a string to an IO handle for usage in `config_files()`.

        Using this, you can create a file with the string as its content on the simulated node.
        """
        return io.BytesIO(bytes(s, encoding='UTF-8'))

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj['load_modules'] = self.load_modules
        json_obj['kcmd_append'] = self.kcmd_append
        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        instance.load_modules = utils_base.get_json_attr_top(json_obj, 'load_modules')
        instance.kcmd_append = utils_base.get_json_attr_top(json_obj, 'kcmd_append')
        return instance


class LinuxHost(BaseLinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers: list[str] = []
        self.hostname: str | None = 'ubuntu'

    def cleanup_cmds(self, inst: instantiation.Instantiation) -> list[str]:
        return super().cleanup_cmds(inst) + ['poweroff -f']

    def prepare_pre_cp(self, inst: instantiation.Instantiation) -> list[str]:
        """Commands to run to prepare node before checkpointing."""
        cmds = [
            'set -x',
            'export HOME=/root',
            'export LANG=en_US',
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
            if d[0] == '/':
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

            if com._ip is None:
                continue

            # Force MAC if requested TODO: FIXME
            # if "force_mac_addr" in i.parameters:
            #     mac = i.parameters["force_mac_addr"]
            #     l.append(f"ip link set dev {ifn} address " f"{mac}")

            # Bring interface up
            cmds.append(f"ip link set dev {ifn} up")

            # Add IP addresses if included
            cmds.append(f"ip addr add {com._ip}/24 dev {ifn}")

        return cmds

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj['drivers'] = self.drivers
        json_obj['hostname'] = self.hostname
        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        instance.drivers = utils_base.get_json_attr_top(json_obj, 'drivers')
        instance.hostname = utils_base.get_json_attr_top(json_obj, 'hostname')
        return instance


class I40ELinuxHost(LinuxHost):
    def __init__(self, sys: base.System) -> None:
        super().__init__(sys)
        self.drivers.append('i40e')


class E1000LinuxHost(LinuxHost):

    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers.append('e1000')


class NVMeLinuxHost(LinuxHost):

    def __init__(self, sys: base.System) -> None:
        super().__init__(sys)
        self.drivers.append('nvme')


class EnsoHost(LinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers: list[str] = []
        self.hostname: str | None = 'ubuntu'
        self.memory = 16 * 1024
        self.enso_parent_dir = '/root'
        self.local_enso_dir: tp.Optional[str] = None
        self.vm_mount_name = 'enso'

        enso_img = system.DistroDiskImage(sys, 'enso')
        self.add_disk(enso_img)

    @property
    def enso_dir(self) -> str:
        return f'{self.enso_parent_dir}/{self.vm_mount_name}'

    def cleanup_cmds(self, inst: instantiation.Instantiation) -> list[str]:
        return super().cleanup_cmds(inst) + ['poweroff -f']

    def prepare_pre_cp(self, inst: instantiation.Instantiation) -> list[str]:
        """Commands to run to prepare node before checkpointing."""
        cmds = [
            'set -x',
            'export HOME=/root',
            'export LANG=en_US',
            'export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:'
            + '/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"',
            'mount -t proc proc /proc',
            'mount -t sysfs none /sys',
            'lspci -tvv',
            'grep HUGETLB /boot/config-$(uname -r)',
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

        if self.local_enso_dir is not None:
            cmds += [
                f'mkdir -p {self.enso_parent_dir}/{self.vm_mount_name}-extract',
                (
                    f'tar xf /tmp/guest/{self.vm_mount_name}'
                    f' -C {self.enso_parent_dir}/{self.vm_mount_name}-extract'
                ),
                # Rsync using checksum to to avoid copying files that are not
                # modified.
                (
                    f"rsync -a --exclude='build*' --checksum "
                    f"{self.enso_parent_dir}/{self.vm_mount_name}-extract/"
                    f"{self.vm_mount_name} "
                    f"{self.enso_parent_dir}"
                )
            ]

        cmds += [
            f'cd {self.enso_dir}/build',
            'ninja -v',
            'sudo ninja install',
        ]

        for d in self.drivers:
            if d[0] == '/':
                cmds.append(f"insmod {d}")
            else:
                cmds.append(f"modprobe {d}")

        # Set up hugepages.
        cmds += [
            "sudo mkdir -p /mnt/huge",
            (
                'bash -c "(sudo mount | grep /mnt/huge) > /dev/null'
                ' || sudo mount -t hugetlbfs hugetlbfs /mnt/huge"'
            ),
            (
                'bash -c "echo 4096 | sudo tee /sys/devices/system/node/node0/'
                'hugepages/hugepages-2048kB/nr_hugepages"'
            ),
        ]

        # Load the kernel module.
        cmds += [
            f'cd {self.enso_dir}/software/kernel/linux/',
            'export SHELLOPTS',
            'bash -x ./install',
        ]
        return cmds

    # pylint: disable=consider-using-with
    def config_files(self, inst: instantiation.Instantiation) -> tp.Dict[str, tp.IO]:
        files = super().config_files(inst)
        if self.local_enso_dir is not None:
            # Tar the directory to be copied to the VM.
            tar_path = f'/tmp/{self.vm_mount_name}.tar'
            with tarfile.open(tar_path, 'w') as tar:
                tar.add(self.local_enso_dir, arcname='enso')

            files[self.vm_mount_name] = open(tar_path, 'rb')

        return files

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj['drivers'] = self.drivers
        json_obj['hostname'] = self.hostname
        json_obj['enso_parent_dir'] = self.enso_parent_dir
        json_obj['local_enso_dir'] = self.local_enso_dir
        json_obj['vm_mount_name'] = self.vm_mount_name
        return json_obj

    @classmethod
    def fromJSON(cls, system: base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        instance.drivers = utils_base.get_json_attr_top(json_obj, 'drivers')
        instance.hostname = utils_base.get_json_attr_top(json_obj, 'hostname')
        instance.enso_parent_dir = utils_base.get_json_attr_top(
            json_obj, 'enso_parent_dir'
        )
        instance.local_enso_dir = utils_base.get_json_attr_top(
            json_obj, 'local_enso_dir'
        )
        instance.vm_mount_name = utils_base.get_json_attr_top(
            json_obj, 'vm_mount_name'
        )
        return instance
