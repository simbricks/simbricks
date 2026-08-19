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

import abc
import enum
import os
import pathlib
import shutil
import tempfile
import typing as tp
import zipfile

import pydantic


def _write_files_to_zip(
    zip_file: zipfile.ZipFile, file_list: list[tuple[pathlib.Path, pathlib.Path]]
) -> None:
    for source, dest in file_list:
        zip_file.write(filename=source, arcname=dest)


def _add_file_to_zip_list(
    file_list: list[tuple[pathlib.Path, pathlib.Path]],
    file_path: pathlib.Path,
    base_path: pathlib.Path,
    relative: bool,
) -> None:
    file_path = file_path.resolve()
    base_path = base_path.resolve()

    if not file_path.is_file():
        raise Exception(f"_add_file_to_zip: cannot add non file {file_path} to zip")

    if relative:
        if not file_path.is_relative_to(base_path):
            raise RuntimeError(f"file path {file_path} is not relative to base path {base_path}")

        file_list.append((file_path, file_path.relative_to(base_path)))
    else:
        file_list.append((file_path, file_path))


def _add_to_zip_list(
    file_list: list[tuple[pathlib.Path, pathlib.Path]],
    path: pathlib.Path,
    base_path: pathlib.Path,
    relative: bool,
    recursive: bool,
) -> None:
    if path.is_file():
        _add_file_to_zip_list(file_list, path, base_path, relative)
    elif path.is_dir() and recursive:
        for child_path in path.rglob("*"):
            if child_path.is_file():
                _add_file_to_zip_list(file_list, child_path, base_path, relative)
    else:
        raise Exception(f"_add_to_zip: cannot add {str(path)} to zip")


# create an artifact containing all files and folders specified as paths.
def create_artifact(
    file: str | tp.IO[bytes],
    paths_to_include: list[str] = [],
    base_path: pathlib.Path = pathlib.Path("./"),
    check_relative: bool = False,
    recursive: bool = True,
    flat: bool = False,
) -> None:
    if len(paths_to_include) < 1:
        return

    base_path = base_path.resolve()

    file_list: list[tuple[pathlib.Path, pathlib.Path]] = []

    for path_str in paths_to_include:
        path = pathlib.Path(base_path, path_str).resolve()
        if check_relative and not path.is_relative_to(base_path):
            raise RuntimeError("output artifact path must be relative to work directory")
        if flat:
            base_zip = path.parent
        else:
            base_zip = base_path
        _add_to_zip_list(file_list, path, base_zip, check_relative or flat, recursive)

    # Sort files to add them in a deterministic order
    file_list.sort(key=lambda elm: elm[1])

    with zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED) as zip_file:
        _write_files_to_zip(zip_file, file_list)


def unpack_artifact(file: str | tp.IO[bytes], dest_path: str) -> None:
    with zipfile.ZipFile(file, "r") as zip_file:
        zip_file.extractall(dest_path)


class ArtifactKind(str, enum.Enum):
    """What an artifact is for, and therefore which way it travels."""

    #: Produced by a run, executor -> main runner.
    OUTPUT = "output"
    #: Input for a whole instantiation, main runner -> executor.
    INSTANTIATION_INPUT = "instantiation_input"
    #: Input for a single fragment, main runner -> executor.
    FRAGMENT_INPUT = "fragment_input"


class ArtifactInfo(pydantic.BaseModel):
    """
    What identifies an artifact, wherever it happens to be on its way.
    """

    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")

    kind: ArtifactKind
    name: str
    run_id: str
    run_fragment_id: str


class Artifact(pydantic.BaseModel):
    """A packed artifact held as a file, and what it is."""

    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")

    path: pathlib.Path
    info: ArtifactInfo


class ArtifactSink(abc.ABC):
    """
    Destination for a completed artifact.

    Callers use :meth:`produce`; implementations provide :meth:`store`.
    """

    @abc.abstractmethod
    async def store(self, artifact: Artifact) -> None:
        """
        Consume the complete artifact.

        Must not return before it is durably handed off. The caller owns the
        file and deletes it afterwards, so an implementation that wants to keep
        it has to move or copy it.
        """

    async def produce(
        self,
        info: ArtifactInfo,
        *,
        paths_to_include: list[str],
        base_path: pathlib.Path,
        staging_dir: pathlib.Path,
        check_relative: bool = True,
    ) -> None:
        """
        Pack ``paths_to_include`` into an artifact and hand it to this sink.

        ``staging_dir`` must lie outside ``base_path``, so the artifact cannot
        end up inside itself, and should be on the same filesystem as a
        filesystem sink's destination, so storing it stays a rename.
        """
        if not paths_to_include:
            return

        staging_dir.mkdir(parents=True, exist_ok=True)
        handle, staged_path = tempfile.mkstemp(
            dir=staging_dir, prefix=".artifact-", suffix=".partial"
        )
        os.close(handle)
        staged = pathlib.Path(staged_path)
        try:
            create_artifact(
                file=str(staged),
                paths_to_include=paths_to_include,
                base_path=base_path,
                check_relative=check_relative,
            )
            await self.store(Artifact(path=staged, info=info))
        finally:
            staged.unlink(missing_ok=True)


class LocalFsArtifactSink(ArtifactSink):
    """
    Keeps artifacts in a directory on the local filesystem.

    This is the sink used when there is no backend to upload to.
    """

    def __init__(self, base_dir: pathlib.Path) -> None:
        self._base_dir = base_dir

    async def store(self, artifact: Artifact) -> None:
        dest = self._base_dir / artifact.info.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(artifact.path, dest)
        except OSError:
            # Staging and destination are on different filesystems, so the
            # rename cannot work and the bytes have to be copied instead.
            shutil.copyfile(artifact.path, dest)
