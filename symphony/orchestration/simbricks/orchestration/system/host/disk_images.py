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
import io
import pathlib
import tarfile
import typing as tp
from simbricks.utils import base as utils_base
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.system import base as sys_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.system import host as sys_host
    from simbricks.orchestration.simulation import base as sim_base


class DiskImage(utils_base.IdObj):
    def __init__(self, h: sys_host.Host) -> None:
        super().__init__()
        self.host: sys_host.Host = h
        self._qemu_img_exec: str = "sims/external/qemu/build/qemu-img"

    @abc.abstractmethod
    def available_formats(self) -> list[str]:
        return []

    @abc.abstractmethod
    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        raise Exception("must be overwritten")

    async def make_qcow_copy(
        self,
        inst: inst_base.Instantiation,
        format: str,
        sim: sim_base.Simulator
    ) -> str:
        disk_path = pathlib.Path(self.path(inst=inst, format=format))
        copy_path = inst.join_imgs_path(relative_path=f"hdcopy.{self._id}")
        prep_cmds = [
            (
                f"{inst.join_repo_base(relative_path=self._qemu_img_exec)} create -f qcow2 -F qcow2 -o "
                f'backing_file="{disk_path}" '
                f"{copy_path}"
            )
        ]
        await inst._cmd_executor.exec_simulator_prepare_cmds(sim, prep_cmds)
        return copy_path

    @staticmethod
    def assert_is_file(path: str) -> str:
        if not pathlib.Path(path).is_file():
            raise Exception(f"path={path} must be a file")

    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        pass

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        # Find first supported disk image format in order of simulator pref.
        sim = inst.find_sim_by_spec(self.host)
        format = None
        av_fmt = self.available_formats()
        for f in sim.supported_image_formats():
            if f in av_fmt:
                format = f
                break

        if format is None:
            raise Exception("No supported image format found")

        await self._prepare_format(inst, format)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["type"] = self.__class__.__name__
        json_obj["module"] = self.__class__.__module__
        json_obj["host"] = self.host.id()
        json_obj["qemu_img_exec"] = self._qemu_img_exec
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> DiskImage:
        instance = super().fromJSON(json_obj)
        host_id = int(utils_base.get_json_attr_top(json_obj, "host"))
        instance.host = system.get_comp(host_id)
        instance._qemu_img_exec = utils_base.get_json_attr_top(
            json_obj, "qemu_img_exec"
        )
        return instance


# Disk image where user just provides a path
class ExternalDiskImage(DiskImage):
    def __init__(self, h: sys_host.FullSystemHost, path: str) -> None:
        super().__init__(h)
        self._path = path
        self.formats = ["raw", "qcow2"]

    def available_formats(self) -> list[str]:
        return self.formats

    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        DiskImage.assert_is_file(self._path)
        return self._path

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["path"] = self._path
        json_obj["formats"] = self.formats
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> DiskImage:
        instance = super().fromJSON(system, json_obj)
        instance._path = utils_base.get_json_attr_top(json_obj, "path")
        instance.formats = utils_base.get_json_attr_top(json_obj, "formats")
        return instance


# Disk images shipped with simbricks
class DistroDiskImage(DiskImage):
    def __init__(self, h: sys_host.FullSystemHost, name: str) -> None:
        super().__init__(h)
        self.name = name
        self.formats = ["raw", "qcow2"]

    def available_formats(self) -> list[str]:
        return self.formats

    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        path = inst.hd_path(self.name)
        if format == "raw":
            path += ".raw"
        elif format == "qcow2":
            pass
        else:
            raise RuntimeError("Unsupported disk format")
        DiskImage.assert_is_file(path)
        return path

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["name"] = self.name
        json_obj["formats"] = self.formats
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> DiskImage:
        instance = super().fromJSON(system, json_obj)
        instance.name = utils_base.get_json_attr_top(json_obj, "name")
        instance.formats = utils_base.get_json_attr_top(json_obj, "formats")
        return instance


# Abstract base class for dynamically generated images
class DynamicDiskImage(DiskImage):
    def __init__(self, h: sys_host.FullSystemHost) -> None:
        super().__init__(h)

    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        return inst.dynamic_img_path(self, format)

    @abc.abstractmethod
    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        pass

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> DynamicDiskImage:
        return super().fromJSON(system, json_obj)


# Builds the Tar with the commands to run etc.
class LinuxConfigDiskImage(DynamicDiskImage):
    def __init__(self, h: sys_host.LinuxHost) -> None:
        super().__init__(h)
        self.host: sys_host.LinuxHost

    def available_formats(self) -> list[str]:
        return ["raw"]

    async def make_qcow_copy(
        self, inst: inst_base.Instantiation, format: str, sim: sim_base.Simulator
    ) -> str:
        return self.path(inst=inst, format=format)

    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        path = self.path(inst, format)
        with tarfile.open(path, "w:") as tar:
            # add main run script
            cfg_i = tarfile.TarInfo("guest/run.sh")
            cfg_i.mode = 0o777
            cfg_f = self.host.strfile(self.host.config_str(inst))
            cfg_f.seek(0, io.SEEK_END)
            cfg_i.size = cfg_f.tell()
            cfg_f.seek(0, io.SEEK_SET)
            tar.addfile(tarinfo=cfg_i, fileobj=cfg_f)
            cfg_f.close()

            # add additional config files
            for n, f in self.host.config_files(inst).items():
                f_i = tarfile.TarInfo("guest/" + n)
                f_i.mode = 0o777
                f.seek(0, io.SEEK_END)
                f_i.size = f.tell()
                f.seek(0, io.SEEK_SET)
                tar.addfile(tarinfo=f_i, fileobj=f)
                f.close()

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> LinuxConfigDiskImage:
        return super().fromJSON(system, json_obj)


# This is an additional example: building disk images directly from python
# Could of course also have a version that generates the packer config from
# python
class PackerDiskImage(DynamicDiskImage):
    def __init__(self, h: sys_host.FullSystemHost, packer_config_path: str) -> None:
        super().__init__(h)
        self.config_path = packer_config_path

    def available_formats(self) -> list[str]:
        return ["raw", "qcow"]

    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        # TODO: invoke packer to build the image if necessary
        pass

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["config_path"] = self.config_path
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> PackerDiskImage:
        instance = super().fromJSON(system, json_obj)
        instance.config_path = utils_base.get_json_attr_top(json_obj, "config_path")
        return instance
