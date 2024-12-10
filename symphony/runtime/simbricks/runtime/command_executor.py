# Copyright 2021 Max Planck Institute for Software Systems, and
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
import os
import pathlib
import shlex
import shutil
import signal
import typing as tp
from asyncio.subprocess import Process


class OutputListener:

    def __init__(self):
        self.cmd_parts: list[str] = []

    @abc.abstractmethod
    async def handel_err(self, lines: list[str]) -> None:
        pass

    @abc.abstractmethod
    async def handel_out(self, lines: list[str]) -> None:
        pass

    def toJSON(self) -> dict:
        return {
            "cmd": self.cmd_parts,
        }


class LegacyOutputListener(OutputListener):

    def __init__(self):
        super().__init__()
        self.stdout: list[str] = []
        self.stderr: list[str] = []
        self.merged_output: list[str] = []

    def _add_to_lists(self, extend: list[str], to_add_to: list[str]) -> None:
        if isinstance(extend, list):
            to_add_to.extend(extend)
            self.merged_output.extend(extend)
        else:
            raise Exception("ComponentOutputHandle: can only add str or list[str] to outputs")

    async def handel_out(self, lines: list[str]) -> None:
        self._add_to_lists(extend=lines, to_add_to=self.stdout)

    async def handel_err(self, lines: list[str]) -> None:
        self._add_to_lists(extend=lines, to_add_to=self.stderr)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj.update(
            {
                "stdout": self.stdout,
                "stderr": self.stderr,
                "merged_output": self.merged_output,
            }
        )
        return json_obj


class Component(object):

    def __init__(self, cmd_parts: tp.List[str], with_stdin=False):
        self.is_ready = False
        self.stdout_buf = bytearray()
        self.stderr_buf = bytearray()
        self.cmd_parts: list[str] = cmd_parts
        self._output_handler: list[OutputListener] = []
        self.with_stdin: bool = with_stdin

        self._proc: Process
        self._terminate_future: asyncio.Task

    def subscribe(self, listener: OutputListener) -> None:
        listener.cmd_parts = self.cmd_parts
        self._output_handler.append(listener)

    def _parse_buf(self, buf: bytearray, data: bytes) -> tp.List[str]:
        if data is not None:
            buf.extend(data)
        lines = []
        start = 0
        for i in range(0, len(buf)):
            if buf[i] == ord("\n"):
                l = buf[start:i].decode("utf-8")
                lines.append(l)
                start = i + 1
        del buf[0:start]

        if len(data) == 0 and len(buf) > 0:
            lines.append(buf.decode("utf-8"))
        return lines

    async def _consume_out(self, data: bytes) -> None:
        eof = len(data) == 0
        ls = self._parse_buf(self.stdout_buf, data)
        if len(ls) > 0 or eof:
            await self.process_out(ls, eof=eof)
            for h in self._output_handler:
                await h.handel_out(ls)

    async def _consume_err(self, data: bytes) -> None:
        eof = len(data) == 0
        ls = self._parse_buf(self.stderr_buf, data)
        if len(ls) > 0 or eof:
            await self.process_err(ls, eof=eof)
            for h in self._output_handler:
                await h.handel_err(ls)

    async def _read_stream(self, stream: asyncio.StreamReader, fn):
        while True:
            bs = await stream.readline()
            if bs:
                await fn(bs)
            else:
                await fn(bs)
                return

    async def _waiter(self) -> None:
        stdout_handler = asyncio.create_task(self._read_stream(self._proc.stdout, self._consume_out))
        stderr_handler = asyncio.create_task(self._read_stream(self._proc.stderr, self._consume_err))
        rc = await self._proc.wait()
        await asyncio.gather(stdout_handler, stderr_handler)
        await self.terminated(rc)

    async def send_input(self, bs: bytes, eof=False) -> None:
        self._proc.stdin.write(bs)
        if eof:
            self._proc.stdin.close()

    async def start(self) -> None:
        if self.with_stdin:
            stdin = asyncio.subprocess.PIPE
        else:
            stdin = asyncio.subprocess.DEVNULL

        self._proc = await asyncio.create_subprocess_exec(
            *self.cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=stdin,
        )
        self._terminate_future = asyncio.create_task(self._waiter())
        await self.started()

    async def wait(self) -> None:
        """
        Wait for running process to finish and output to be collected.

        On cancellation, the `CancelledError` is propagated but this component
        keeps running.
        """
        await asyncio.shield(self._terminate_future)

    async def interrupt(self) -> None:
        """Sends an interrupt signal."""
        if self._proc.returncode is None:
            self._proc.send_signal(signal.SIGINT)

    async def terminate(self) -> None:
        """Sends a terminate signal."""
        if self._proc.returncode is None:
            self._proc.terminate()

    async def kill(self) -> None:
        """Sends a kill signal."""
        if self._proc.returncode is None:
            self._proc.kill()

    async def int_term_kill(self, delay: int = 5) -> None:
        """Attempts to stop this component by sending signals in the following
        order: interrupt, terminate, kill."""
        await self.interrupt()
        try:
            await asyncio.wait_for(self._proc.wait(), delay)
            return
        # before Python 3.11, asyncio.wait_for() throws asyncio.TimeoutError -_-
        except (TimeoutError, asyncio.TimeoutError):
            print(f"terminating component {self.cmd_parts[0]} " f"pid {self._proc.pid}", flush=True)
            await self.terminate()

        try:
            await asyncio.wait_for(self._proc.wait(), delay)
            return
        except (TimeoutError, asyncio.TimeoutError):
            print(f"killing component {self.cmd_parts[0]} " f"pid {self._proc.pid}", flush=True)
            await self.kill()
        await self._proc.wait()

    async def sigusr1(self) -> None:
        """Sends an interrupt signal."""
        if self._proc.returncode is None:
            self._proc.send_signal(signal.SIGUSR1)

    async def started(self) -> None:
        pass

    async def terminated(self, rc) -> None:
        pass

    async def process_out(self, lines: tp.List[str], eof: bool) -> None:
        pass

    async def process_err(self, lines: tp.List[str], eof: bool) -> None:
        pass


class SimpleComponent(Component):

    def __init__(self, label: str, cmd_parts: tp.List[str], *args, verbose=True, canfail=False, **kwargs) -> None:
        self.label = label
        self.verbose = verbose
        self.canfail = canfail
        self.cmd_parts = cmd_parts
        super().__init__(cmd_parts, *args, **kwargs)

    async def process_out(self, lines: tp.List[str], eof: bool) -> None:
        if self.verbose:
            for _ in lines:
                print(self.label, "OUT:", lines, flush=True)

    async def process_err(self, lines: tp.List[str], eof: bool) -> None:
        if self.verbose:
            for _ in lines:
                print(self.label, "ERR:", lines, flush=True)

    async def terminated(self, rc: int) -> None:
        if self.verbose:
            print(self.label, "TERMINATED:", rc, flush=True)
        if not self.canfail and rc != 0:
            raise RuntimeError("Command Failed: " + str(self.cmd_parts))


class Executor(abc.ABC):

    def __init__(self) -> None:
        self.ip = None

    @abc.abstractmethod
    def create_component(self, label: str, parts: tp.List[str], **kwargs) -> SimpleComponent:
        pass

    @abc.abstractmethod
    async def await_file(self, path: str, delay=0.05, verbose=False) -> None:
        pass

    @abc.abstractmethod
    async def send_file(self, path: str, verbose=False) -> None:
        pass

    @abc.abstractmethod
    async def mkdir(self, path: str, verbose=False) -> None:
        pass

    @abc.abstractmethod
    async def rmtree(self, path: str, verbose=False) -> None:
        pass

    # runs the list of commands as strings sequentially
    async def run_cmdlist(self, label: str, cmds: tp.List[str], verbose=True) -> None:
        i = 0
        for cmd in cmds:
            cmd_c = self.create_component(label + "." + str(i), shlex.split(cmd), verbose=verbose)
            await cmd_c.start()
            await cmd_c.wait()

    async def await_files(self, paths: tp.List[str], *args, **kwargs) -> None:
        xs = []
        for p in paths:
            waiter = asyncio.create_task(self.await_file(p, *args, **kwargs))
            xs.append(waiter)

        await asyncio.gather(*xs)


class LocalExecutor(Executor):

    def create_component(self, label: str, parts: list[str], **kwargs) -> SimpleComponent:
        return SimpleComponent(label, parts, **kwargs)

    async def await_file(self, path: str, delay=0.05, verbose=False, timeout=30) -> None:
        if verbose:
            print(f"await_file({path})")
        t = 0
        while not os.path.exists(path):
            if t >= timeout:
                raise TimeoutError()
            await asyncio.sleep(delay)
            t += delay

    async def send_file(self, path: str, verbose=False) -> None:
        # locally we do not need to do anything
        pass

    async def mkdir(self, path: str, verbose=False) -> None:
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

    async def rmtree(self, path: str, verbose=False) -> None:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path):
            os.unlink(path)
