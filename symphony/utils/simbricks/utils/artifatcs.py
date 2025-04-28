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
    check_relative: bool,
) -> None:
    if not file_path.is_file():
        raise Exception(f"_add_file_to_zip: cannot add non file {file_path} to zip")

    if check_relative:
        file_path = file_path.resolve()
        if not file_path.is_relative_to(base_path):
            raise RuntimeError(f"file path {file_path} is not relative to base path {base_path}")

        zip_file.write(filename=file_path, arcname=file_path.relative_to(base_path))
    else:
        zip_file.write(filename=file_path, arcname=file_path)


def _add_folder_to_zip(
    zip_file: zipfile.ZipFile, dir_path: pathlib.Path, base_path: pathlib.Path, check_relative: bool
) -> None:
    if dir_path.is_file():
        _add_file_to_zip(zip_file, dir_path, base_path, check_relative)
        return
    elif dir_path.is_dir():
        for child_path in dir_path.rglob("*"):
            if child_path.is_file():
                _add_file_to_zip(zip_file, child_path, base_path, check_relative)
    else:
        raise Exception(f"_add_folder_to_zip: cannot add {str(dir_path)} to zip")


# create an artifact containing all files and folders specified as paths.
def create_artifact(
    file: str | tp.IO[bytes],
    paths_to_include: list[str] = [],
    base_path: pathlib.Path = pathlib.Path("./"),
    check_relative: bool = False,
) -> None:
    if len(paths_to_include) < 1:
        return

    base_path = base_path.resolve()

    with zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path_str in paths_to_include:
            path = pathlib.Path(path_str)
            if check_relative:
                full_path = (base_path / path).resolve()
                if (path.is_absolute() or not full_path.is_relative_to(base_path)):
                    raise RuntimeError(f"invalid path {full_path}")
            else:
                full_path = path
            if full_path.is_file():
                _add_file_to_zip(zip_file, full_path, base_path, check_relative)
            else:
                _add_folder_to_zip(zip_file, full_path, base_path, check_relative)


def unpack_artifact(file: str | tp.IO[bytes], dest_path: str) -> None:
    with zipfile.ZipFile(file, "r") as zip_file:
        zip_file.extractall(dest_path)
