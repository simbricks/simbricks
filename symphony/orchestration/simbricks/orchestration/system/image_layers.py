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
import shlex
import shutil
import typing as tp

import typing_extensions as tpe

from simbricks.orchestration.system import disk_images, image_cache
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

    @abc.abstractmethod
    def hash_parts(self, inst: inst_base.Instantiation) -> list[str]:
        """What this layer contributes to the image's content hash.

        Everything that changes what the layer does to the image, and nothing
        that does not -- an id or a scratch path would make every run unique.
        """

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

    def hash_parts(self, inst: inst_base.Instantiation) -> list[str]:
        parts = ["add-files", self.dest_dir, str(self.mode)]
        for file in self.files:
            with file.IOHandle(inst) as handle:
                parts += [file.file_name, disk_images.hash_file(handle)]
        return parts

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

    def hash_parts(self, inst: inst_base.Instantiation) -> list[str]:
        return ["run-command", self.cmd]

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

    def hash_parts(self, inst: inst_base.Instantiation) -> list[str]:
        with self.file.IOHandle(inst) as handle:
            return ["run-script", disk_images.hash_file(handle)]

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
        self.qemu_img_exec = "qemu-img"
        """What the image, and the chain it may be a delta on, are manipulated
        with -- here and in the backends, which all build qcow2."""

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

    def prefix_hashes(self, inst: inst_base.Instantiation) -> list[str]:
        """Content hash after each layer, so a build can start from the longest
        prefix that was cached. The first entry is the base with no layers.

        The builder class is in the seed: the same layers on the same base give
        different images depending on which backend ran them.
        """
        cls = type(self)
        seed = [
            "layered",
            self.base.content_hash(inst),
            f"{cls.__module__}.{cls.__qualname__}",
            str(self.disk_size),
        ]
        hashes = [disk_images.hash_strings(seed)]
        for layer in self.layers:
            hashes.append(disk_images.hash_strings([hashes[-1]] + layer.hash_parts(inst)))
        return hashes

    def content_hash(self, inst: inst_base.Instantiation) -> str:
        return self.prefix_hashes(inst)[-1]

    def _base_format(self, format: str) -> str:
        """Format to ask the base image for. Prefer the one we are producing."""
        available = self.base.available_formats()
        return format if format in available else available[0]

    async def _build_from_base(self, inst: inst_base.Instantiation, format: str, out: str) -> None:
        # The base is not attached to a host, so nothing else prepares it.
        base_format = self._base_format(format)
        await self.base._prepare_format(inst, base_format)
        await self._run_build(inst, format, self.base.path(inst, base_format), self.layers, out)

    async def _run_build(
        self,
        inst: inst_base.Instantiation,
        format: str,
        source: str,
        layers: list[ImageLayer],
        out: str,
        overlay: bool = False,
    ) -> None:
        await self.build(inst, format, source, layers, out, overlay)
        if not pathlib.Path(out).is_file():
            raise RuntimeError(f"image build produced no output at '{out}'")

    async def _store_build(
        self,
        inst: inst_base.Instantiation,
        cache: image_cache.ImageCache,
        hashes: list[str],
        scratch: pathlib.Path,
    ) -> None:
        """Build what the cache does not have yet and keep it, as a delta on the
        longest run of layers already there.

        A delta rather than a whole image because that is the difference between
        a cache entry costing megabytes and costing gigabytes -- appending a
        layer to a cached image stores only what that layer wrote.
        """
        built = (scratch / "delta.qcow2").as_posix()
        pathlib.Path(built).unlink(missing_ok=True)

        for done in range(len(self.layers) - 1, -1, -1):
            parent = cache.image(hashes[done])
            if parent is None or not pathlib.Path(parent).is_file():
                continue
            await self._run_build(
                inst, image_cache.FORMAT, parent, self.layers[done:], built, overlay=True
            )
            # Record where the parent sits relative to this entry, not where it
            # happens to be now: that is what lets the chain be hard linked
            # somewhere else and still resolve.
            await self.rebase_image(inst, built, f"../{hashes[done]}/{image_cache.IMAGE}")
            cache.store_image(hashes[-1], built, parent=hashes[done])
            return

        await self._build_from_base(inst, image_cache.FORMAT, built)
        cache.store_image(hashes[-1], built)

    async def _take_out(
        self,
        inst: inst_base.Instantiation,
        cache: image_cache.ImageCache,
        digest: str,
        out: str,
        format: str,
    ) -> None:
        """Give this run the image, without copying what it does not have to.

        For qcow2 the chain is hard linked into the run and the simulator gets a
        fresh overlay on top of it, so a cache hit copies nothing and the run
        survives the entries being evicted behind it. A simulator that cannot
        read a chain gets it flattened -- once, kept in the entry for the next
        run to link.
        """
        chain_dir = inst.env.img_dir(f"chain.{self.id()}")
        if format == image_cache.FORMAT:
            leaf = cache.materialize_chain(digest, chain_dir)
            if leaf is None:
                raise RuntimeError(f"image cache entry '{digest}' is incomplete")
            await self.overlay_image(inst, leaf, out)
            return

        flat = cache.flat(digest, format)
        if flat is not None and cache.take_out(flat, out):
            return
        leaf = cache.materialize_chain(digest, chain_dir)
        if leaf is None:
            raise RuntimeError(f"image cache entry '{digest}' is incomplete")
        await self.convert_image(inst, leaf, out, format)
        cache.store_flat(digest, format, out)

    async def _prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        out = self.path(inst, format)
        async with inst.prepare_lock(out):
            if pathlib.Path(out).is_file():
                return
            cache = image_cache.for_instantiation(inst)
            if cache is None:
                await self._build_from_base(inst, format, out)
                return

            hashes = self.prefix_hashes(inst)
            scratch = pathlib.Path(inst.env.img_dir(f"build.{self.id()}"))
            scratch.mkdir(parents=True, exist_ok=True)

            # Held across the build, so a second run wanting the same image
            # waits for this one rather than building it again.
            async with cache.locked(hashes[-1]):
                cached = cache.image(hashes[-1])
                if cached is None:
                    await self._store_build(inst, cache, hashes, scratch)
                    cached = cache.image(hashes[-1])
                if cached is None:
                    raise RuntimeError("the image was built but is not in the cache")
                try:
                    await self._take_out(inst, cache, hashes[-1], out, format)
                except Exception:
                    # Promised an image the cache then could not give us:
                    # another machine sharing it may have evicted the entry
                    # since. Building it here is better than failing the run.
                    pathlib.Path(out).unlink(missing_ok=True)
                    await self._build_from_base(inst, format, out)
                else:
                    cache.used(hashes[-1])

            limit = inst.env.image_cache_size()
            if limit is not None:
                # After a store, the only moment the cache grows.
                cache.evict(limit)

    async def boot_artifacts(
        self, inst: inst_base.Instantiation, kinds: list[disk_images.BootArtifact]
    ) -> dict[disk_images.BootArtifact, str]:
        """Boot files for this image, from the cache when a previous run put them
        there. That is what makes them survive a cache hit, where no build runs
        and a backend that collects them while building never gets the chance.
        """
        if not kinds:
            return {}
        out_dir = pathlib.Path(inst.env.img_dir(f"boot.{self.id()}"))
        out_dir.mkdir(parents=True, exist_ok=True)
        cache = image_cache.for_instantiation(inst)
        digest = self.content_hash(inst) if cache is not None else ""

        async with inst.prepare_lock(out_dir.as_posix()):
            wanted = [k for k in kinds if not (out_dir / k.value).is_file()]
            if cache is None:
                if wanted:
                    await self._produce_boot_artifacts(inst, wanted, out_dir)
                self._check_boot_artifacts(kinds, out_dir)
                return {k: (out_dir / k.value).as_posix() for k in kinds}

            # Under the entry's lock: a sweep in another run may be evicting,
            # and it leaves alone whatever is held.
            async with cache.locked(digest):
                for kind in list(wanted):
                    cached = cache.boot_artifact(digest, kind.value)
                    if cached is not None and cache.take_out(
                        cached, (out_dir / kind.value).as_posix()
                    ):
                        wanted.remove(kind)
                if wanted:
                    await self._produce_boot_artifacts(inst, wanted, out_dir)
                self._check_boot_artifacts(kinds, out_dir)
                for kind in kinds:
                    # Also for the ones the build itself collected, which is how
                    # a backend that only gets them while building survives a hit.
                    if cache.boot_artifact(digest, kind.value) is None:
                        cache.store_boot_artifact(
                            digest, kind.value, (out_dir / kind.value).as_posix()
                        )
                cache.used(digest)

        return {k: (out_dir / k.value).as_posix() for k in kinds}

    @staticmethod
    def _check_boot_artifacts(kinds: list[disk_images.BootArtifact], out_dir: pathlib.Path) -> None:
        for kind in kinds:
            if not (out_dir / kind.value).is_file():
                raise RuntimeError(f"'{kind.value}' was not produced for this image")

    async def _produce_boot_artifacts(
        self,
        inst: inst_base.Instantiation,
        kinds: list[disk_images.BootArtifact],
        out_dir: pathlib.Path,
    ) -> None:
        """Put @kinds into @out_dir, named by kind. Called only for the ones
        neither this run nor the cache already has."""
        raise RuntimeError(
            f"{self.__class__.__name__} cannot provide boot artifacts {[k.value for k in kinds]}"
        )

    @abc.abstractmethod
    async def build(
        self,
        inst: inst_base.Instantiation,
        format: str,
        base_path: str,
        layers: list[ImageLayer],
        out_path: str,
        overlay: bool = False,
    ) -> None:
        """Produce @out_path in @format from @base_path by applying @layers.

        With @overlay, @out_path holds only what the layers changed and reads
        the rest from @base_path, which it must therefore keep referring to.
        """

    def _require_qemu_img(self) -> str:
        """Check qemu-img is there, so a missing one is reported here and by name.

        Not a dependency of the package: qemu is not packaged for conda, so
        this being installed says nothing about it being available.
        """
        if shutil.which(self.qemu_img_exec) is None:
            raise RuntimeError(
                f"'{self.qemu_img_exec}' not found: building a layered image needs"
                " qemu-utils installed on the runner"
            )
        return self.qemu_img_exec

    async def convert_image(
        self, inst: inst_base.Instantiation, source: str, out: str, format: str
    ) -> None:
        """Write @source, and anything it is a delta on, to @out as one @format image."""
        partial = f"{out}.partial"
        await inst.command_executor.exec_prepare_cmds(
            [shlex.join([self._require_qemu_img(), "convert", "-O", format, source, partial])]
        )
        pathlib.Path(partial).rename(out)

    async def overlay_image(self, inst: inst_base.Instantiation, backing: str, out: str) -> None:
        """Put an empty image at @out that reads everything from @backing."""
        await inst.command_executor.exec_prepare_cmds(
            [
                shlex.join(
                    [
                        self._require_qemu_img(),
                        "create",
                        "-q",
                        "-f",
                        image_cache.FORMAT,
                        "-F",
                        image_cache.FORMAT,
                        "-b",
                        backing,
                        out,
                    ]
                )
            ]
        )

    async def rebase_image(self, inst: inst_base.Instantiation, image: str, backing: str) -> None:
        """Record @backing as where @image reads what it does not hold itself.
        Changes nothing about the contents of either."""
        # -u rewrites where the image says its backing is and touches no data,
        # which is what we want: the data is already right, the path is not.
        await inst.command_executor.exec_prepare_cmds(
            [
                shlex.join(
                    [
                        self._require_qemu_img(),
                        "rebase",
                        "-q",
                        "-u",
                        "-f",
                        image_cache.FORMAT,
                        "-F",
                        image_cache.FORMAT,
                        "-b",
                        backing,
                        image,
                    ]
                )
            ]
        )

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["base"] = self.base.id()
        json_obj["disk_size"] = self.disk_size
        json_obj["qemu_img_exec"] = self.qemu_img_exec
        json_obj["layers"] = [layer.toJSON() for layer in self.layers]
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(system, json_obj)
        # The base has to exist before an image layering on it can be built, so
        # it has the lower id and System.fromJSON already deserialized it.
        instance.base = system._get_disk_image(utils_base.get_json_attr_top(json_obj, "base"))
        instance.disk_size = utils_base.get_json_attr_top_or_none(json_obj, "disk_size")
        instance.qemu_img_exec = utils_base.get_json_attr_top(json_obj, "qemu_img_exec")
        instance.layers = [
            utils_base.get_cls_by_json(layer).fromJSON(layer)
            for layer in utils_base.get_json_attr_top(json_obj, "layers")
        ]
        return instance
