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
import zipfile


def _add_file_to_zip(zip_file: zipfile.ZipFile, file_path: str) -> None:
    path = pathlib.Path(file_path)
    if not path.is_file():
        raise Exception(f"_add_file_to_zip: cannot add non file {path} to zip")

    zip_file.write(filename=file_path, arcname=path)


def _add_folder_to_zip(zip_file: zipfile.ZipFile, dir_path: str) -> None:
    path = pathlib.Path(dir_path)
    if path.is_file():
        _add_file_to_zip(zip_file=zip_file, file_path=path)
        return
    elif path.is_dir():
        for child_path in path.rglob("*"):
            if child_path.is_file():
                _add_file_to_zip(zip_file=zip_file, file_path=child_path)
    else:
        raise Exception(f"_add_folder_to_zip: cannot add {path} to zip")


# create an artifact containing all files and folders specified as paths.
def create_artifact(artifact_name: str = "simbricks-artifact.zip", paths_to_include: list[str] = []) -> None:
    if len(paths_to_include) < 1:
        return

    with zipfile.ZipFile(artifact_name, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in paths_to_include:
            path_obj = pathlib.Path(path)
            if path_obj.is_file():
                _add_file_to_zip(zip_file=zip_file, file_path=path_obj)
            else:
                _add_folder_to_zip(zip_file=zip_file, dir_path=path_obj)
