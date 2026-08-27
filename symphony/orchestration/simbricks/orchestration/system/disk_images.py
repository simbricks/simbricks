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
import asyncio
import io
import pathlib
import tarfile
import typing as tp

import typing_extensions as tpe

from simbricks.utils import base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.simulation import host as sim_host
    from simbricks.orchestration.system import base as sys_base
    from simbricks.orchestration.system.host import base as sys_host


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
    def assert_is_file(path: str) -> None:
        if not pathlib.Path(path).is_file():
            raise Exception(f"path={path} must be a file")

    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        pass

    # Determining the format should actually happen in the simulator, since it is the choice of the
    # host simulator what disk image format it wants to use. The choice in the simulator is
    # constrained by the supported formats of the disk image. This also allows the simulator to
    # implement a simulator specific strategy to pick the format (e.g. a format precedence).
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

    # It is a bit ugly that we use HostSim here. This method should directly get the needed format,
    # so that it can prepare it. See also comment on find_format above.
    async def prepare(self, inst: inst_base.Instantiation, host: sys_host.Host) -> None:
        sim = inst.find_sim_by_spec(host)
        # A system host should be simulated by a HostSim. We assume this here.
        sim = tp.cast("sim_host.HostSim", sim)
        format = self.find_format(sim)

        await self._prepare_format(inst, format)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["needs_copy"] = self.needs_copy
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.needs_copy = utils_base.get_json_attr_top(json_obj, "needs_copy")
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
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
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
        path = inst.env.work_dir_or_abs(self._path)
        DiskImage.assert_is_file(path)
        return path

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["path"] = self._path
        json_obj["formats"] = self.formats
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
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
        path = inst.env.global_input_dir(f"images/{self.name}/{self.name}", True)
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
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
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
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
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
            for file in self.host.config_files(inst):
                f_i = tarfile.TarInfo(f"guest/{file.file_name}")
                f_i.mode = 0o777
                f = file.IOHandle(inst)
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
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
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

        # --var and its value have to be separate arguments
        command = ["packer", "build"]
        for key, val in self.vars.items():
            command.extend(["--var", f"{key}={val}"])
        command.append(self.config_path)

        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        if stdout.strip():
            await inst.command_executor.msg_info(stdout.decode("utf-8", errors="replace"))

        if process.returncode == 0:
            await inst.command_executor.msg_info("packer image built successfully")
        else:
            await inst.command_executor.msg_error(stderr.decode("utf-8", errors="replace"))
            raise RuntimeError("failed to build image with packer")

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["config_path"] = self.config_path
        json_obj["vars"] = utils_base.dict_to_json(self.vars)
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        instance._prepared = False
        instance.config_path = utils_base.get_json_attr_top(json_obj, "config_path")
        vars_json = utils_base.get_json_attr_top(json_obj, "vars")
        instance.vars = utils_base.json_to_dict(vars_json)
        return instance


class ConfigFile(utils_base.IdObj, utils_base.InputArtifactSource):
    def __init__(self, file_name: str):
        super().__init__()
        # Name of the file in the image
        self.file_name: str = file_name

    def input_artifact_files(self) -> list[str]:
        return []

    @abc.abstractmethod
    def IOHandle(self, inst: inst_base.Instantiation) -> tp.IO:
        pass

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["file_name"] = self.file_name
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.file_name = utils_base.get_json_attr_top(json_obj, "file_name")
        return instance


class ConfigFileLocal(ConfigFile):
    def __init__(self, file_name: str, path: str):
        super().__init__(file_name)
        # Path of the local file to be added to the image
        self.path: str = path
        self.open_mode: str = "rb"

    def IOHandle(self, inst: inst_base.Instantiation) -> tp.IO:
        path = inst.env.work_dir_or_abs(self.path, True)
        return open(path, self.open_mode)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["path"] = self.path
        json_obj["open_mode"] = self.open_mode
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.path = utils_base.get_json_attr_top(json_obj, "path")
        instance.open_mode = utils_base.get_json_attr_top(json_obj, "open_mode")
        return instance


class ConfigFileStr(ConfigFile):
    def __init__(self, file_name: str, string: str):
        super().__init__(file_name)
        self.string = string

    def IOHandle(self, inst: inst_base.Instantiation) -> tp.IO:
        return io.BytesIO(bytes(self.string, encoding="UTF-8"))

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["string"] = self.string
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.string = utils_base.get_json_attr_top(json_obj, "string")
        return instance


class ConfigFileArtifact(ConfigFile):
    """Local filei, shipped to the runner if necessary as input artifact."""

    def __init__(self, file_name: str, path: str):
        super().__init__(file_name)
        # Path of the local file, relative to where the script defining the system runs
        self.path: str = pathlib.Path(path).resolve().as_posix()
        # Name the file has inside the artifact, which is currently packed flat
        self.artifact_file_name: str = pathlib.PurePath(self.path).name
        self.open_mode: str = "rb"

    def input_artifact_files(self) -> list[str]:
        return [self.path]

    def IOHandle(self, inst: inst_base.Instantiation) -> tp.IO:
        artifact_path = pathlib.Path(inst.env.input_artifacts_dir(), self.artifact_file_name)
        if artifact_path.exists():
            return open(artifact_path, self.open_mode)
        # Local runs build no input artifact, the file is still where it was picked up
        local_path = pathlib.Path(self.path)
        if not local_path.exists():
            raise RuntimeError(
                f"config file '{self.file_name}' was neither shipped as an input artifact nor"
                f" available locally at '{self.path}'"
            )
        return open(local_path, self.open_mode)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["path"] = self.path
        json_obj["artifact_file_name"] = self.artifact_file_name
        json_obj["open_mode"] = self.open_mode
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.path = utils_base.get_json_attr_top(json_obj, "path")
        instance.artifact_file_name = utils_base.get_json_attr_top(json_obj, "artifact_file_name")
        instance.open_mode = utils_base.get_json_attr_top(json_obj, "open_mode")
        return instance
