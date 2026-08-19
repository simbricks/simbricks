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
import typing


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


def remove_matching(directory: pathlib.Path, pattern: str) -> None:
    """Delete the files in ``directory`` whose name matches ``pattern``."""
    if not directory.is_dir():
        return
    for match in directory.glob(pattern):
        if match.is_file():
            match.unlink()


def is_absolute_exists(path: str) -> bool:
    pl_path = pathlib.Path(path)
    return pl_path.is_absolute() and pl_path.is_file()


def join_paths(base: str | os.PathLike[str], relative_path: str, must_exist=False) -> str:
    if relative_path.startswith("/"):
        raise Exception(
            f"cannot join with base={base} because relative_path={relative_path} starts with '/'"
        )

    joined = pathlib.Path(base, relative_path).resolve()
    if must_exist and not joined.exists():
        raise Exception(f"Joined path does not exist: {str(joined)}")
    return joined.as_posix()


def build_path_resolver(
    relative_to_conda_env: str,
    custom_env: str | None,
    relative_to_custom_env: str | None,
    file_relative_to_base: str,
) -> typing.Callable[[str | None], str]:
    """
    Build a resolver that turns an optional user-provided path into a concrete one.

    Simulator objects are built on the *client* but run on the *executor*. In between they
    are serialized and rebuilt via ``fromJSON``, which does **not** run ``__init__``. So a
    path computed in ``__init__`` reaches the executor as a literal string: an absolute
    path valid only on the client's machine. Instead, keep what the user passed (usually
    ``None`` = "use the default") in the serialized state and resolve it on the executor,
    at the point of use. This captures the *rules* for finding a file rather than the
    result of applying them, so they are evaluated wherever the resolver is called — which
    means: never call it on the client and store the result.

    Resolution order: an explicit non-empty path is returned unchanged; otherwise the base
    is ``$custom_env[/relative_to_custom_env]`` if that variable is set, else
    ``$CONDA_PREFIX/relative_to_conda_env``, with ``file_relative_to_base`` appended.
    If neither variable is set the prefix degrades to ``""``, yielding a root-anchored
    path.

    Args:
        relative_to_conda_env: Install root relative to ``$CONDA_PREFIX``.
        custom_env: Environment variable that replaces the conda prefix when set on the
            executor.
        relative_to_custom_env: Optional subdirectory appended to ``custom_env``.
        file_relative_to_base: Path of the file itself, relative to the resolved base.

    Returns:
        A callable taking the user-provided path (or ``None``/``""`` for the default).

    Example:
            ...

            def __init__(
                self,
                simulation: sim_base.Simulation,
                executable: str | None = None,
                config: str | None = None,
            ):
                super().__init__(
                    simulation=simulation,
                    executable="" if executable is None else executable,
                )
                self.resolve_exe = build_path_resolver(
                    "opt", "GEM5_PREFIX", None, "gem5/build/X86/gem5"
                )
                self.resolve_conf = build_path_resolver(
                    "opt", "GEM5_PREFIX", None, "gem5/configs/simbricks/simbricks.py"
                )

            ...

            def run_cmd(self, inst: inst_base.Instantiation) -> str:
                exe = self.resolve_exe(self._executable)
                conf = self.resolve_conf(self._config)

            ...
    """

    def resolve_path(to_resolve: str | None) -> str:
        custom_prefix = os.environ.get(custom_env) if custom_env else None
        if custom_prefix is not None:
            base = f"{custom_prefix}"
            if relative_to_custom_env:
                base += f"/{relative_to_custom_env}"
        else:
            conda_prefix = os.environ.get("CONDA_PREFIX")
            if conda_prefix is None:
                conda_prefix = ""
            base = f"{conda_prefix}/{relative_to_conda_env}"

        if to_resolve is None or to_resolve == "":
            return f"{base}/{file_relative_to_base}"
        else:
            return to_resolve

    return resolve_path
