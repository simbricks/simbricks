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

"""Image builds with packer, in a booted guest.

Layers run over SSH in a real VM, so anything that needs services running or a
kernel of its own works here. That costs a full boot per build, which the
guestfs backend avoids -- prefer it unless a booted guest is the point.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import shlex
import shutil
import tarfile
import typing as tp
import uuid

import typing_extensions as tpe

from simbricks.orchestration.system import disk_images, image_layers
from simbricks.utils import base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.system import base as sys_base

_DATA_DIR = pathlib.Path(__file__).parent / "data"
# Where the layer scripts find the files their layers carry.
_GUEST_INPUT_DIR = "/tmp/input"


def _require(exe: str) -> str:
    """Check a tool is present, so a missing one is reported here and by name."""
    if shutil.which(exe) is None:
        raise RuntimeError(
            f"'{exe}' not found: PackerImage needs packer, qemu and xorriso installed on the runner"
        )
    return exe


class PackerImage(image_layers.LayeredDiskImage):
    """A layered image built by booting the base image under packer."""

    def __init__(self, system: sys_base.System, base: disk_images.DiskImage) -> None:
        super().__init__(system, base)
        self.packer_exec = "packer"
        self.qemu_img_exec = "qemu-img"
        self.qemu_binary = "qemu-system-x86_64"
        self.accelerator: str | None = None
        """Passed to packer. None picks kvm where the runner has it, else tcg."""
        self.mem_size = "2G"
        """RAM for the machine packer boots to run the layers in."""
        self.cpus = 2
        self.ssh_username = "ubuntu"
        self.ssh_password = "ubuntu"
        self.ssh_timeout: str | None = None
        """How long packer waits for SSH. None allows for the accelerator: without
        kvm a boot that takes seconds takes many minutes."""
        self.cleanup = True
        """Run the harness cleanup (apt caches, logs, fstrim) after the layers."""

    def available_formats(self) -> list[str]:
        return ["raw", "qcow2"]

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["packer_exec"] = self.packer_exec
        json_obj["qemu_img_exec"] = self.qemu_img_exec
        json_obj["qemu_binary"] = self.qemu_binary
        json_obj["accelerator"] = self.accelerator
        json_obj["mem_size"] = self.mem_size
        json_obj["cpus"] = self.cpus
        json_obj["ssh_username"] = self.ssh_username
        json_obj["ssh_password"] = self.ssh_password
        json_obj["ssh_timeout"] = self.ssh_timeout
        json_obj["cleanup"] = self.cleanup
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        instance.packer_exec = utils_base.get_json_attr_top(json_obj, "packer_exec")
        instance.qemu_img_exec = utils_base.get_json_attr_top(json_obj, "qemu_img_exec")
        instance.qemu_binary = utils_base.get_json_attr_top(json_obj, "qemu_binary")
        instance.accelerator = utils_base.get_json_attr_top_or_none(json_obj, "accelerator")
        instance.mem_size = utils_base.get_json_attr_top(json_obj, "mem_size")
        instance.cpus = utils_base.get_json_attr_top(json_obj, "cpus")
        instance.ssh_username = utils_base.get_json_attr_top(json_obj, "ssh_username")
        instance.ssh_password = utils_base.get_json_attr_top(json_obj, "ssh_password")
        instance.ssh_timeout = utils_base.get_json_attr_top_or_none(json_obj, "ssh_timeout")
        instance.cleanup = utils_base.get_json_attr_top(json_obj, "cleanup")
        return instance

    # ---- building ----------------------------------------------------------

    def _scratch_dir(self, inst: inst_base.Instantiation) -> pathlib.Path:
        path = pathlib.Path(inst.env.img_dir(f"build.{self.id()}"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _boot_dir(self, inst: inst_base.Instantiation) -> pathlib.Path:
        return pathlib.Path(inst.env.img_dir(f"boot.{self.id()}"))

    def _write_seed(self, scratch: pathlib.Path) -> list[str]:
        """Assemble the cloud-init seed, which packer attaches as a CD.

        The instance id is fresh every build, so cloud-init redoes the
        per-instance setup on an already provisioned base image.
        """
        seed = scratch / "seed"
        seed.mkdir(parents=True, exist_ok=True)
        (seed / "meta-data").write_text(f"instance-id: simbricks-{uuid.uuid4()}\n")
        files = [seed / "meta-data"]
        for name in ("user-data", "network-config"):
            target = seed / name
            target.write_bytes((_DATA_DIR / "seed" / name).read_bytes())
            files.append(target)
        return [f.as_posix() for f in files]

    def _write_script(self, path: pathlib.Path, body: str) -> pathlib.Path:
        path.write_text(f"#!/bin/sh\nset -eu\n{body}")
        path.chmod(0o755)
        return path

    def _materialize(
        self,
        inst: inst_base.Instantiation,
        file: disk_images.ConfigFile,
        directory: pathlib.Path,
    ) -> pathlib.Path:
        """Write a config file out for the input tarball to carry into the guest."""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / file.file_name
        with file.IOHandle(inst) as src, open(path, "wb") as dst:
            while chunk := src.read(1 << 20):
                dst.write(chunk)
        # Modes survive the tarball, so settle them here rather than in the guest.
        path.chmod(0o644)
        return path

    def _lower_layers(
        self,
        inst: inst_base.Instantiation,
        layers: list[image_layers.ImageLayer],
        scratch: pathlib.Path,
    ) -> tuple[list[str], bool]:
        """Write every layer out as a guest script. Returns them and whether any carries files."""
        scripts_dir = scratch / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        scripts: list[str] = []
        carries_files = False

        for index, layer in enumerate(layers):
            ident = f"l{index}"
            if isinstance(layer, image_layers.RunCommand):
                script = self._write_script(scripts_dir / f"{ident}.sh", f"{layer.cmd}\n")
            elif isinstance(layer, image_layers.RunScript):
                script = self._materialize(inst, layer.file, scripts_dir / ident)
                script.chmod(0o755)
            elif isinstance(layer, image_layers.AddFiles):
                carries_files = True
                dest_dir = layer.dest_dir or "/"
                body = [f"mkdir -p {shlex.quote(dest_dir)}"]
                for file in layer.files:
                    self._materialize(inst, file, scratch / "input" / ident)
                    src = f"{_GUEST_INPUT_DIR}/{ident}/{file.file_name}"
                    dest = pathlib.PurePosixPath(dest_dir, file.file_name).as_posix()
                    mode = f"-m {layer.mode:04o} " if layer.mode is not None else ""
                    body.append(f"install {mode}{shlex.quote(src)} {shlex.quote(dest)}")
                script = self._write_script(scripts_dir / f"{ident}.sh", "\n".join(body) + "\n")
            else:
                raise RuntimeError(f"PackerImage cannot build layer {type(layer).__name__}")
            scripts.append(script.as_posix())

        return scripts, carries_files

    async def _disk_size(self, base_path: str) -> str:
        """What to give packer, which resizes the copy it boots.

        Always a concrete size: packer has a default of its own, and letting
        that apply would silently grow images nobody asked to grow. Never below
        the base's own size, which packer would refuse anyway. In megabytes with
        the suffix, because packer reads a bare number as megabytes.
        """
        proc = await asyncio.create_subprocess_exec(
            _require(self.qemu_img_exec),
            "info",
            "--output=json",
            base_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"could not read '{base_path}': {stderr.decode(errors='replace')}")
        base_size = int(json.loads(stdout)["virtual-size"])
        wanted = image_layers.parse_size(self.disk_size) if self.disk_size else 0
        megabytes = -(-max(base_size, wanted) // (1 << 20))
        return f"{megabytes}M"

    def _ssh_timeout(self) -> str:
        if self.ssh_timeout is not None:
            return self.ssh_timeout
        return "20m" if self._accelerator() == "kvm" else "90m"

    def _accelerator(self) -> str:
        if self.accelerator is not None:
            return self.accelerator
        return "kvm" if os.access("/dev/kvm", os.R_OK | os.W_OK) else "tcg"

    async def build(
        self,
        inst: inst_base.Instantiation,
        format: str,
        base_path: str,
        layers: list[image_layers.ImageLayer],
        out_path: str,
    ) -> None:
        scratch = self._scratch_dir(inst)
        # Packer refuses to write into a directory that already exists, and a
        # previous attempt in this run may have left one.
        out_dir = scratch / "out"
        shutil.rmtree(out_dir, ignore_errors=True)
        boot_tar = scratch / "boot.tar"
        boot_tar.unlink(missing_ok=True)

        seed_files = self._write_seed(scratch)
        scripts, carries_files = self._lower_layers(inst, layers, scratch)
        cmds = []
        input_tar = scratch / "input.tar.gz"
        if carries_files:
            # Packed from inside the directory: the template unpacks it into
            # /tmp/input, and a leading input/ here would nest under it.
            cmds.append(
                shlex.join(
                    ["tar", "czf", input_tar.as_posix(), "-C", (scratch / "input").as_posix(), "."]
                )
            )

        variables = {
            "source_image": base_path,
            "source_checksum": "none",
            "seed_files": json.dumps(seed_files),
            "name": f"{self.id()}.qcow2",
            "output": out_dir.as_posix(),
            "scripts": json.dumps(scripts),
            "input": input_tar.as_posix() if carries_files else "",
            "boot_artifacts": boot_tar.as_posix(),
            "cleanup_script": (_DATA_DIR / "cleanup.sh").as_posix() if self.cleanup else "",
            "serial_log": (scratch / "serial.log").as_posix(),
            "disk_size": await self._disk_size(base_path),
            # packer counts in megabytes here.
            "memory": str(-(-image_layers.parse_size(self.mem_size) // (1 << 20))),
            "cpus": str(self.cpus),
            "qemu_binary": self.qemu_binary,
            "accelerator": self._accelerator(),
            "ssh_username": self.ssh_username,
            "ssh_password": self.ssh_password,
            "ssh_timeout": self._ssh_timeout(),
        }
        template = (_DATA_DIR / "image.pkr.hcl").as_posix()
        # What packer builds the seed CD with.
        _require("xorriso")
        # A no-op once the qemu builder plugin is installed, which the executor
        # image does ahead of time so a build needs no network for it.
        cmds.append(shlex.join([_require(self.packer_exec), "init", template]))
        build = [self.packer_exec, "build"]
        for key, value in variables.items():
            build += ["-var", f"{key}={value}"]
        cmds.append(shlex.join(build + [template]))

        await inst.command_executor.exec_prepare_cmds(cmds)

        built = out_dir / f"{self.id()}.qcow2"
        if not built.is_file():
            raise RuntimeError(f"packer produced no image at '{built}'")
        if format == "qcow2":
            built.rename(out_path)
        else:
            await inst.command_executor.exec_prepare_cmds(
                [
                    shlex.join(
                        [
                            _require(self.qemu_img_exec),
                            "convert",
                            "-O",
                            format,
                            built.as_posix(),
                            out_path,
                        ]
                    )
                ]
            )
        self._unpack_boot_artifacts(inst, boot_tar)

    # ---- boot artifacts ----------------------------------------------------

    def _unpack_boot_artifacts(self, inst: inst_base.Instantiation, boot_tar: pathlib.Path) -> None:
        """Unpack what the guest handed us. Downloaded during the build: the VM
        is gone by the time a simulator asks."""
        out_dir = self._boot_dir(inst)
        out_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(boot_tar) as tar:
            for member in tar.getmembers():
                name = pathlib.PurePosixPath(member.name).name
                if not member.isfile() or not name:
                    continue
                source = tar.extractfile(member)
                assert source is not None
                with source, open(out_dir / name, "wb") as dst:
                    shutil.copyfileobj(source, dst)
        boot_tar.unlink(missing_ok=True)

    async def _produce_boot_artifacts(
        self,
        inst: inst_base.Instantiation,
        kinds: list[disk_images.BootArtifact],
        out_dir: pathlib.Path,
    ) -> None:
        # The build downloads these from the guest, so reaching here means the
        # image came from the cache and its entry does not have them.
        missing = [k.value for k in kinds]
        msg = (
            f"{missing} not available for this image: packer collects boot artifacts while"
            " it builds, and this image was not built in this run."
        )
        if disk_images.BootArtifact.VMLINUX in kinds:
            msg += (
                " An uncompressed vmlinux also needs the kernel's debug package"
                " installed by a layer."
            )
        raise RuntimeError(msg)
