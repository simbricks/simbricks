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
import asyncio
import typing as tp
from simbricks.utils import base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.system.host import base as sys_host
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.system import base as sys_base
    from simbricks.orchestration.simulation import host as sim_host


class DiskImage(utils_base.IdObj):
    def __init__(self, system: sys_base.System) -> None:
        super().__init__()
        system._add_disk_image(self)
        self.needs_copy = True

    @abc.abstractmethod
    def available_formats(self) -> list[str]:
        return []

    @abc.abstractmethod
    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        raise Exception("must be overwritten")

    @staticmethod
    def assert_is_file(path: str) -> str:
        if not pathlib.Path(path).is_file():
            raise Exception(f"path={path} must be a file")

    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        pass

    def find_format(self, host: sim_host.HostSim) -> str:
        # Find first supported disk image format in order of simulator pref.
        format = None
        av_fmt = self.available_formats()
        for f in host.supported_image_formats():
            if f in av_fmt:
                format = f
                break

        if format is None:
            raise Exception("No supported image format found")

        return format

    async def prepare(self, inst: inst_base.Instantiation, host: sys_host.Host) -> None:
        sim = inst.find_sim_by_spec(host)
        format = self.find_format(sim)

        await self._prepare_format(inst, format)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["needs_copy"] = self.needs_copy
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> DiskImage:
        instance = super().fromJSON(json_obj)
        instance.needs_copy = utils_base.get_json_attr_top(json_obj, "needs_copy")
        system._add_disk_image(instance)
        return instance

    def add_host(self, host: sys_host.Host) -> None:
        pass


class DummyDiskImage(DiskImage):
    def __init__(self, system: sys_base.System) -> None:
        super().__init__(system)

    def available_formats(self) -> list[str]:
        raise RuntimeError("cannot call abstract method 'available_formats' of DummyDiskImage")

    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        raise RuntimeError("cannot call abstract method 'path' of DummyDiskImage")

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> DummyDiskImage:
        instance = super().fromJSON(system, json_obj)
        instance._is_dummy = True
        return instance


# Disk image where user just provides a path
class ExternalDiskImage(DiskImage):
    def __init__(self, system: sys_base.System, path: str) -> None:
        super().__init__(system)
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
    def __init__(self, system: sys_base.System, name: str) -> None:
        super().__init__(system)
        self.name = name
        self.formats = ["raw", "qcow2"]

    def available_formats(self) -> list[str]:
        return self.formats

    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        path = inst.env.hd_path(self.name)
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
    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        return inst.env.dynamic_img_path(self, format)

    @abc.abstractmethod
    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        pass

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> DynamicDiskImage:
        return super().fromJSON(system, json_obj)


# Builds the Tar with the commands to run etc.
class LinuxConfigDiskImage(DynamicDiskImage):
    def __init__(self, system: sys_base.System, host: sys_host.BaseLinuxHost):
        super().__init__(system)
        self.host = host
        self.needs_copy = False

    def available_formats(self) -> list[str]:
        return ["raw"]

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

    def toJSON(self):
        json_obj = super().toJSON()
        json_obj["host"] = self.host.id()
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> LinuxConfigDiskImage:
        instance = super().fromJSON(system, json_obj)
        # NOTE: the host gets set during deserialization of the host, since there is a cyclic
        # dependency between host and this disk image during deserialization
        instance.host = None
        return instance

    def add_host(self, host: sys_host.BaseLinuxHost) -> None:
        if self.host is not None:
            raise RuntimeError("tried to set host of LinuxConfigDiskImage twice")
        self.host = host


# This is an additional example: building disk images directly from python
# Could of course also have a version that generates the packer config from
# python
class PackerDiskImage(DynamicDiskImage):
    def __init__(self, system: sys_base.System, packer_config_path: str) -> None:
        super().__init__(system)
        self.config_path = packer_config_path
        self.vars: dict[str, str] = {}
        self._prepared: bool = False

    def available_formats(self) -> list[str]:
        return ["raw", "qcow2"]

    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        if self._prepared:
            return
        self._prepared = True

        # Construct the packer build command
        command = ["packer", "build"]
        for key, val in self.vars.items():
            command.append(f"--var {key}={val}")
        command.append(self.config_path)

        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        print(stdout.decode())

        # Check the return code to determine success
        if process.returncode == 0:
            print("Packer image built successfully!")
        else:
            print(stderr.decode())
            raise RuntimeError("failed to build image with packer")

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["config_path"] = self.config_path
        json_obj["vars"] = utils_base.dict_to_json(self.vars)
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> PackerDiskImage:
        instance = super().fromJSON(system, json_obj)
        instance._prepared = False
        instance.config_path = utils_base.get_json_attr_top(json_obj, "config_path")
        vars_json = utils_base.get_json_attr_top(json_obj, "vars")
        instance.vars = utils_base.json_to_dict(vars_json)
        return instance
