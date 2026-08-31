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

"""A disk image built as a base image plus an ordered list of changes.

Layers are declarative rather than shell, so the same list can be lowered to
virt-customize flags, packer scripts, or Dockerfile instructions. None of the
three operations is distro-specific: installing a package is just a command.
File payloads are ConfigFiles, which already handle getting a local file to the
runner.
"""

from __future__ import annotations

import abc
import os
import pathlib
import re
import typing as tp

import typing_extensions as tpe

from simbricks.orchestration.system import disk_images
from simbricks.utils import base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.system import base as sys_base


class ImageLayer(utils_base.IdObj, utils_base.InputArtifactSource):
    """One step in building an image."""

    def config_files(self) -> list[disk_images.ConfigFile]:
        """Files this layer puts into the image, if any."""
        return []

    def input_artifact_files(self) -> list[str]:
        files = []
        for file in self.config_files():
            files += file.input_artifact_files()
        return files

    @classmethod
    def fromJSON(cls, json_obj: dict) -> tpe.Self:
        return super().fromJSON(json_obj)


def _config_file_from_json(json_obj: dict) -> disk_images.ConfigFile:
    return utils_base.get_cls_by_json(json_obj).fromJSON(json_obj)


class AddFiles(ImageLayer):
    """Put files into @dest_dir in the image, optionally chmod'ed to @mode."""

    def __init__(
        self,
        files: list[disk_images.ConfigFile],
        dest_dir: str,
        mode: int | None = None,
    ) -> None:
        super().__init__()
        self.files = files
        self.dest_dir = dest_dir
        self.mode = mode

    def config_files(self) -> list[disk_images.ConfigFile]:
        return list(self.files)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["files"] = [f.toJSON() for f in self.files]
        json_obj["dest_dir"] = self.dest_dir
        json_obj["mode"] = self.mode
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.files = [
            _config_file_from_json(f) for f in utils_base.get_json_attr_top(json_obj, "files")
        ]
        instance.dest_dir = utils_base.get_json_attr_top(json_obj, "dest_dir")
        instance.mode = utils_base.get_json_attr_top_or_none(json_obj, "mode")
        return instance


class RunCommand(ImageLayer):
    """Run a shell command inside the image."""

    def __init__(self, cmd: str) -> None:
        super().__init__()
        self.cmd = cmd

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["cmd"] = self.cmd
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.cmd = utils_base.get_json_attr_top(json_obj, "cmd")
        return instance


class RunScript(ImageLayer):
    """Run a script inside the image. Inline or taken from the submitting machine."""

    def __init__(self, file: disk_images.ConfigFile) -> None:
        super().__init__()
        self.file = file

    def config_files(self) -> list[disk_images.ConfigFile]:
        return [self.file]

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["file"] = self.file.toJSON()
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.file = _config_file_from_json(utils_base.get_json_attr_top(json_obj, "file"))
        return instance


_SIZE_UNITS = {"": 1, "K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40}


def parse_size(size: str) -> int:
    """Bytes for a size written the way qemu and packer take it, e.g. "32G"."""
    match = re.fullmatch(r"\s*(\d+)\s*([KMGT]?)B?\s*", size, re.IGNORECASE)
    if not match:
        raise ValueError(f"'{size}' is not a size like '512M' or '32G'")
    return int(match.group(1)) * _SIZE_UNITS[match.group(2).upper()]


class LayeredDiskImage(disk_images.DynamicDiskImage, utils_base.InputArtifactSource):
    """A base image plus layers, built when the simulation is prepared.

    Subclasses supplying the build live in their own packages, so a runner only
    installs the tooling for the ways it builds images. Failing to import one is
    the intended signal that a runner cannot build this image.
    """

    def __init__(self, system: sys_base.System, base: disk_images.DiskImage) -> None:
        super().__init__(system)
        self.base = base
        self.layers: list[ImageLayer] = []
        self.disk_size: str | None = None
        """Grow the image to this size, e.g. "32G", before the layers run. None
        keeps the base's size, and a size below it is left alone rather than
        shrinking the image. Not a layer: the build materializes one image, so
        this can only happen as it is created."""

    def add_layer(self, layer: ImageLayer) -> ImageLayer:
        self.layers.append(layer)
        return layer

    def run(self, cmd: str) -> ImageLayer:
        """Run a shell command in the image."""
        return self.add_layer(RunCommand(cmd))

    def run_script(self, path: disk_images.StrPath) -> ImageLayer:
        """Run a script taken from the submitting machine."""
        return self.add_layer(
            RunScript(disk_images.ConfigFileArtifact(os.path.basename(path), path))
        )

    def run_script_str(self, name: str, script: str) -> ImageLayer:
        """Run a script given inline."""
        return self.add_layer(RunScript(disk_images.ConfigFileStr(name, script)))

    def add_file(self, dest: str, content: str, mode: int | None = None) -> ImageLayer:
        """Write @content to @dest in the image."""
        dest_path = pathlib.PurePosixPath(dest)
        return self.add_layer(
            AddFiles(
                [disk_images.ConfigFileStr(dest_path.name, content)],
                dest_path.parent.as_posix(),
                mode,
            )
        )

    def copy_in(self, src: disk_images.StrPath, dest: str, mode: int | None = None) -> ImageLayer:
        """Copy a file from the submitting machine to @dest in the image."""
        dest_path = pathlib.PurePosixPath(dest)
        return self.add_layer(
            AddFiles(
                [disk_images.ConfigFileArtifact(dest_path.name, src)],
                dest_path.parent.as_posix(),
                mode,
            )
        )

    def input_artifact_files(self) -> list[str]:
        files = []
        for layer in self.layers:
            files += layer.input_artifact_files()
        return files

    def _base_format(self, format: str) -> str:
        """Format to ask the base image for. Prefer the one we are producing."""
        available = self.base.available_formats()
        return format if format in available else available[0]

    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        out = self.path(inst, format)
        async with inst.prepare_lock(out):
            if pathlib.Path(out).is_file():
                return
            # The base is not attached to a host, so nothing else prepares it.
            base_format = self._base_format(format)
            await self.base._prepare_format(inst, base_format)
            await self.build(inst, format, self.base.path(inst, base_format), self.layers, out)
            if not pathlib.Path(out).is_file():
                raise RuntimeError(f"image build produced no output at '{out}'")

    @abc.abstractmethod
    async def build(
        self,
        inst: inst_base.Instantiation,
        format: str,
        base_path: str,
        layers: list[ImageLayer],
        out_path: str,
    ) -> None:
        """Produce @out_path in @format from @base_path by applying @layers."""

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["base"] = self.base.id()
        json_obj["disk_size"] = self.disk_size
        json_obj["layers"] = [layer.toJSON() for layer in self.layers]
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        # The base has to exist before an image layering on it can be built, so
        # it has the lower id and System.fromJSON already deserialized it.
        instance.base = system._get_disk_image(utils_base.get_json_attr_top(json_obj, "base"))
        instance.disk_size = utils_base.get_json_attr_top_or_none(json_obj, "disk_size")
        instance.layers = [
            utils_base.get_cls_by_json(layer).fromJSON(layer)
            for layer in utils_base.get_json_attr_top(json_obj, "layers")
        ]
        return instance
