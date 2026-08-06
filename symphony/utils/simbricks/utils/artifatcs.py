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

import pathlib
import typing as tp
import zipfile


def _add_file_to_zip(
    zip_file: zipfile.ZipFile,
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

        zip_file.write(filename=file_path, arcname=file_path.relative_to(base_path))
    else:
        zip_file.write(filename=file_path, arcname=file_path)


def _add_to_zip(
    zip_file: zipfile.ZipFile,
    path: pathlib.Path,
    base_path: pathlib.Path,
    relative: bool,
    recursive: bool,
) -> None:
    if path.is_file():
        _add_file_to_zip(zip_file, path, base_path, relative)
    elif path.is_dir() and recursive:
        for child_path in path.rglob("*"):
            if child_path.is_file():
                _add_file_to_zip(zip_file, child_path, base_path, relative)
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

    with zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path_str in paths_to_include:
            path = pathlib.Path(base_path, path_str).resolve()
            if check_relative and not path.is_relative_to(base_path):
                raise RuntimeError("output artifact path must be relative to work directory")
            if flat:
                base_zip = path.parent
            else:
                base_zip = base_path
            _add_to_zip(zip_file, path, base_zip, check_relative or flat, recursive)


def unpack_artifact(file: str | tp.IO[bytes], dest_path: str) -> None:
    with zipfile.ZipFile(file, "r") as zip_file:
        zip_file.extractall(dest_path)
