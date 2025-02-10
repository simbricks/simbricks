# Copyright 2025 Max Planck Institute for Software Systems, and
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
"""Utility functions for operations on files and directories."""

import asyncio
import os
import pathlib
import shutil


async def await_file(path: str, delay=0.1, verbose=False, timeout=600) -> None:
    if verbose:
        print(f"await_file({path})")
    t = 0
    while not os.path.exists(path):
        if t >= timeout:
            raise TimeoutError()
        await asyncio.sleep(delay)
        t += delay


def mkdir(path: str) -> None:
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def rmtree(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.exists(path):
        os.unlink(path)


def is_absolute_exists(path: str) -> bool:
    pl_path = pathlib.Path(path)
    return pl_path.is_absolute() and pl_path.is_file()


def join_paths(base: str = "", relative_path: str = "", must_exist=False) -> str:
    if relative_path.startswith("/"):
        raise Exception(
            f"cannot join with base={base} because relative_path={relative_path} starts with '/'"
        )

    joined = pathlib.Path(base).joinpath(relative_path).resolve()
    if must_exist and not joined.exists():
        raise Exception(f"Joined path does not exist: {str(joined)}")
    return joined.as_posix()
