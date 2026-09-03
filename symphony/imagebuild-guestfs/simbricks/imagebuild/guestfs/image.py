# Copyright 2026 Max Planck Institute for Software Systems, and
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

"""Offline image builds with libguestfs.

virt-customize applies the whole layer list in one invocation without booting a
VM, so an ordinary change costs seconds. Work needing a booted guest wants the
packer backend instead.
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import pathlib
import re
import shlex
import shutil
import typing as tp

import typing_extensions as tpe

from simbricks.orchestration.system import disk_images, image_layers
from simbricks.utils import base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.system import base as sys_base


def _env() -> list[str]:
    """Force the direct appliance backend unless one is already chosen.

    'direct' needs no libvirt session. env(1) because commands run without a
    shell, inheriting the executor's environment.
    """
    if os.environ.get("LIBGUESTFS_BACKEND"):
        return []
    return ["env", "LIBGUESTFS_BACKEND=direct"]


def _require(exe: str) -> str:
    """Check a tool is present, so a missing one is reported here and by name.

    These cannot be conda dependencies -- neither libguestfs nor qemu is
    packaged for conda -- so the Python package being installed says nothing
    about them being available.
    """
    if shutil.which(exe) is None:
        raise RuntimeError(
            f"'{exe}' not found: GuestfsImage needs libguestfs-tools and qemu-utils"
            " installed on the runner"
        )
    return exe


_SECTOR_BYTES = 512
# What a GPT backup header needs at the end of the disk.
_GPT_TAIL_SECTORS = 34


class GuestfsImage(image_layers.LayeredDiskImage):
    """A layered image built offline with virt-customize."""

    def __init__(self, system: sys_base.System, base: disk_images.DiskImage) -> None:
        super().__init__(system, base)
        self.virt_customize_exec = "virt-customize"
        self.qemu_img_exec = "qemu-img"
        self.guestfish_exec = "guestfish"
        self.grow_filesystem = True
        """Whether disk_size grows the filesystem too, not just the disk and its
        partition. False for a filesystem this cannot grow: do it in a layer
        instead, where the guest's own tools are available."""
        self.virt_filesystems_exec = "virt-filesystems"

    def available_formats(self) -> list[str]:
        return ["raw", "qcow2"]

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["virt_customize_exec"] = self.virt_customize_exec
        json_obj["qemu_img_exec"] = self.qemu_img_exec
        json_obj["guestfish_exec"] = self.guestfish_exec
        json_obj["grow_filesystem"] = self.grow_filesystem
        json_obj["virt_filesystems_exec"] = self.virt_filesystems_exec
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        instance.virt_customize_exec = utils_base.get_json_attr_top(json_obj, "virt_customize_exec")
        instance.qemu_img_exec = utils_base.get_json_attr_top(json_obj, "qemu_img_exec")
        instance.guestfish_exec = utils_base.get_json_attr_top(json_obj, "guestfish_exec")
        instance.grow_filesystem = utils_base.get_json_attr_top(json_obj, "grow_filesystem")
        instance.virt_filesystems_exec = utils_base.get_json_attr_top(
            json_obj, "virt_filesystems_exec"
        )
        return instance

    def _scratch_dir(self, inst: inst_base.Instantiation) -> pathlib.Path:
        path = pathlib.Path(inst.env.img_dir(f"build.{self.id()}"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _materialize(
        self,
        inst: inst_base.Instantiation,
        file: disk_images.ConfigFile,
        scratch: pathlib.Path,
        ident: str,
    ) -> pathlib.Path:
        """Write a config file out so virt-customize has something to copy in."""
        # Per-layer subdirectory: the file name has to be the guest's, and two
        # layers may use the same one.
        directory = scratch / ident
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / file.file_name
        with file.IOHandle(inst) as src, open(path, "wb") as dst:
            while chunk := src.read(1 << 20):
                dst.write(chunk)
        return path

    def _layer_args(
        self,
        inst: inst_base.Instantiation,
        layers: list[image_layers.ImageLayer],
        scratch: pathlib.Path,
    ) -> list[str]:
        """Lower the layers to virt-customize arguments.

        virt-customize applies operations in command-line order, so the layer
        list maps onto it directly.
        """
        args: list[str] = []
        for index, layer in enumerate(layers):
            if isinstance(layer, image_layers.RunCommand):
                args += ["--run-command", layer.cmd]
            elif isinstance(layer, image_layers.RunScript):
                path = self._materialize(inst, layer.file, scratch, f"l{index}")
                path.chmod(0o755)
                args += ["--run", path.as_posix()]
            elif isinstance(layer, image_layers.AddFiles):
                dest_dir = layer.dest_dir or "/"
                args += ["--mkdir", dest_dir]
                for file in layer.files:
                    path = self._materialize(inst, file, scratch, f"l{index}")
                    args += ["--copy-in", f"{path.as_posix()}:{dest_dir}"]
                    if layer.mode is not None:
                        dest = pathlib.PurePosixPath(dest_dir, file.file_name)
                        args += ["--chmod", f"{layer.mode:04o}:{dest.as_posix()}"]
            else:
                raise RuntimeError(f"GuestfsImage cannot build layer {type(layer).__name__}")
        return args

    async def _capture(self, cmd: list[str]) -> str:
        """Run a tool we need the output of, rather than the log."""
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"'{shlex.join(cmd)}' failed: {stderr.decode(errors='replace')}")
        return stdout.decode(errors="replace")

    async def _virtual_size(self, image: str) -> int:
        out = await self._capture([_require(self.qemu_img_exec), "info", "--output=json", image])
        return int(json.loads(out)["virtual-size"])

    async def _partition_to_grow(self, image: str) -> tuple[int, bool, str]:
        """The partition to give the extra space to: its number, whether the
        table is GPT, and the filesystem on it.

        The biggest one: on a cloud image the root filesystem dwarfs the boot
        partitions, and it is the one sitting at the end of the disk.
        """
        out = await self._capture(
            _env() + [_require(self.virt_filesystems_exec), "--all", "--long", "--csv", "-a", image]
        )
        rows = list(csv.reader(out.splitlines()))
        if not rows:
            raise RuntimeError(f"could not read the partitions of '{image}'")
        column = {name: index for index, name in enumerate(rows[0])}
        listed = [r for r in rows[1:] if len(r) == len(rows[0])]

        parts = [r for r in listed if r[column["Type"]] == "partition"]
        if not parts:
            raise RuntimeError(f"no partitions to expand in '{image}'")
        biggest = max(parts, key=lambda r: int(r[column["Size"]]))
        number = re.search(r"(\d+)$", biggest[column["Name"]])
        if number is None:
            raise RuntimeError(f"cannot tell the partition number of '{biggest[column['Name']]}'")

        vfs = ""
        for row in listed:
            if (
                row[column["Type"]] == "filesystem"
                and row[column["Name"]] == biggest[column["Name"]]
            ):
                vfs = row[column["VFS"]]
        # The MBR column is empty on a GPT disk.
        return int(number.group(1)), not biggest[column["MBR"]], vfs

    def _filesystem_grow_cmds(self, device: str, vfs: str) -> list[str]:
        """guestfish fragment growing the filesystem into the resized partition.

        ext can be grown offline; xfs and btrfs only grow what is mounted.
        """
        if vfs.startswith("ext"):
            return [":", "e2fsck-f", device, ":", "resize2fs", device]
        if vfs == "xfs":
            return [":", "mount", device, "/", ":", "xfs-growfs", "/"]
        if vfs == "btrfs":
            return [":", "mount", device, "/", ":", "btrfs-filesystem-resize", "/"]
        raise RuntimeError(
            f"cannot grow a '{vfs}' filesystem on '{device}'. Set grow_filesystem = False"
            " to grow only the disk and its partition, and grow the filesystem yourself in"
            " a layer, where the guest's own tools are available."
        )

    async def _grow_cmds(self, source: str, image: str, wanted: int) -> list[str]:
        """Grow @image to @wanted bytes, its biggest partition, and the filesystem
        on it. The layout is read from @source, the base image the copy is made
        from, because @image does not exist yet.

        In place, so that partition numbers do not change: virt-resize copies
        into a new image and renumbers by disk offset, which on a cloud image
        moves the root partition and breaks a simulator booting /dev/sda1.
        """
        number, gpt, vfs = await self._partition_to_grow(source)
        device = f"/dev/sda{number}"
        # Leave the last sectors for the GPT backup header, which parted needs
        # room for. Harmless on an MBR disk.
        end_sector = wanted // _SECTOR_BYTES - _GPT_TAIL_SECTORS
        guestfish = [_require(self.guestfish_exec), "-a", image, "--rw", "run"]
        if gpt:
            # The backup header still sits where the disk used to end.
            guestfish += [":", "part-expand-gpt", "/dev/sda"]
        guestfish += [":", "part-resize", "/dev/sda", str(number), str(end_sector)]
        if self.grow_filesystem:
            guestfish += self._filesystem_grow_cmds(device, vfs)
        return [
            shlex.join([_require(self.qemu_img_exec), "resize", "-q", image, str(wanted)]),
            shlex.join(_env() + guestfish),
        ]

    async def build(
        self,
        inst: inst_base.Instantiation,
        format: str,
        base_path: str,
        layers: list[image_layers.ImageLayer],
        out_path: str,
    ) -> None:
        scratch = self._scratch_dir(inst)
        # Under a temporary name, so a crashed build leaves nothing the next
        # run would mistake for a finished image.
        partial = f"{out_path}.partial"
        cmds = [
            shlex.join([_require(self.qemu_img_exec), "convert", "-O", format, base_path, partial])
        ]
        wanted = image_layers.parse_size(self.disk_size) if self.disk_size else 0
        if wanted > await self._virtual_size(base_path):
            cmds += await self._grow_cmds(base_path, partial, wanted)
        args = self._layer_args(inst, layers, scratch)
        if args:
            cmds.append(
                shlex.join(_env() + [_require(self.virt_customize_exec), "-a", partial] + args)
            )
        await inst.command_executor.exec_prepare_cmds(cmds)
        pathlib.Path(partial).rename(out_path)
