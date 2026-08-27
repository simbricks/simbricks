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

import asyncio
import shlex
import signal
import typing
from asyncio.subprocess import Process
from collections import abc

from simbricks.orchestration.instantiation import command_executor as inst_cmd_exec
from simbricks.runtime import output

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import proxy as inst_proxy
    from simbricks.orchestration.simulation import base as sim_base
    from simbricks.runtime import simulation_executor as sim_exec


MAX_LINE_LEN = 64 * 1024
"""Maximum length in bytes of a single line of component output."""


class CommandExecutor:
    def __init__(
        self,
        cmd: str,
        label: str,
        started_callback: typing.Callable[[], typing.Awaitable[None]],
        exited_callback: typing.Callable[[int], typing.Awaitable[None]],
        stdout_callback: typing.Callable[[list[str]], typing.Awaitable[None]],
        stderr_callback: typing.Callable[[list[str]], typing.Awaitable[None]],
        message_callback: typing.Callable[
            [output.RuntimeMessageLevel, str], typing.Awaitable[None]
        ],
    ):
        self._stdout_buf = bytearray()
        self._stderr_buf = bytearray()
        self._cmd_parts = shlex.split(cmd)
        self._label = label
        self._started_cb = started_callback
        self._exited_cb = exited_callback
        self._stdout_cb = stdout_callback
        self._stderr_cb = stderr_callback
        self._message_cb = message_callback

        self._proc: Process
        self._terminate_future: asyncio.Task

    def _decode_line(self, raw: bytes | bytearray) -> str:
        # NUL is valid UTF-8 but cannot be stored in the backend's text columns
        return raw.decode("utf-8", errors="replace").replace("\x00", "\ufffd")

    def _parse_buf(self, buf: bytearray, data: bytes) -> list[str]:
        if data is not None:
            buf.extend(data)
        lines = []
        start = 0
        for i in range(0, len(buf)):
            if buf[i] == ord("\n"):
                line = self._decode_line(buf[start:i])
                lines.append(line)
                start = i + 1
        del buf[0:start]

        # flush unterminated output so a line without newline cannot grow the buffer forever
        while len(buf) > MAX_LINE_LEN:
            lines.append(self._decode_line(buf[0:MAX_LINE_LEN]))
            del buf[0:MAX_LINE_LEN]

        if len(data) == 0 and len(buf) > 0:
            lines.append(self._decode_line(buf))
        return lines

    async def _consume_stdout(self, data: bytes) -> None:
        eof = len(data) == 0
        ls = self._parse_buf(self._stdout_buf, data)
        if len(ls) > 0 or eof:
            await self._stdout_cb(ls)

    async def _consume_stderr(self, data: bytes) -> None:
        eof = len(data) == 0
        ls = self._parse_buf(self._stderr_buf, data)
        if len(ls) > 0 or eof:
            await self._stderr_cb(ls)

    async def _consume_stream_loop(
        self, stream: asyncio.StreamReader, consume_fn: abc.Callable[[bytes], abc.Awaitable[None]]
    ) -> None:
        while True:
            bs = await stream.read(8192)
            if bs:
                await consume_fn(bs)
            else:
                await consume_fn(bs)
                return
            await asyncio.sleep(1)

    async def _waiter(self) -> None:
        assert self._proc.stdout is not None and self._proc.stderr is not None
        stdout_handler = asyncio.create_task(
            self._consume_stream_loop(self._proc.stdout, self._consume_stdout)
        )
        stderr_handler = asyncio.create_task(
            self._consume_stream_loop(self._proc.stderr, self._consume_stderr)
        )
        rc = await self._proc.wait()
        await asyncio.gather(stdout_handler, stderr_handler)
        await self._exited_cb(rc)

    async def send_input(self, bs: bytes, eof=False) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.write(bs)
        if eof:
            self._proc.stdin.close()

    async def start(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            *self._cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        await self._started_cb()
        self._terminate_future = asyncio.create_task(self._waiter())

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
            await self._message_cb(
                output.RuntimeMessageLevel.WARNING,
                f"[{self._label}] interrupt timed out, terminating pid {self._proc.pid}",
            )
            await self.terminate()

        try:
            await asyncio.wait_for(self._proc.wait(), delay)
            return
        except (TimeoutError, asyncio.TimeoutError):
            await self._message_cb(
                output.RuntimeMessageLevel.WARNING,
                f"[{self._label}] terminate timed out, killing pid {self._proc.pid}",
            )
            await self.kill()
        await self._proc.wait()

    async def sigusr1(self) -> None:
        """Sends an SIGUSR1 signal."""
        if self._proc.returncode is None:
            self._proc.send_signal(signal.SIGUSR1)


class CommandExecutorFactory(inst_cmd_exec.CommandExecutorFactoryBase):
    def __init__(self, sim_exec_cbs: sim_exec.SimulationExecutorCallbacks):
        self._sim_exec_cbs = sim_exec_cbs

    async def message(self, level: output.RuntimeMessageLevel, msg: str) -> None:
        await self._sim_exec_cbs.simulation_message(level, msg)

    async def msg_info(self, msg: str) -> None:
        await self.message(output.RuntimeMessageLevel.INFO, msg)

    async def msg_warning(self, msg: str) -> None:
        await self.message(output.RuntimeMessageLevel.WARNING, msg)

    async def msg_error(self, msg: str) -> None:
        await self.message(output.RuntimeMessageLevel.ERROR, msg)

    async def exec_prepare_cmds(
        self, cmds: list[str], sim: sim_base.Simulator | None = None
    ) -> None:
        cbs = self._sim_exec_cbs
        for cmd in cmds:
            if sim is None:

                async def started_cb() -> None:
                    await cbs.simulation_prepare_cmd_start(cmd)

                async def stdout_cb(lines: list[str]) -> None:
                    await cbs.simulation_prepare_cmd_stdout(cmd, lines)

                async def stderr_cb(lines: list[str]) -> None:
                    await cbs.simulation_prepare_cmd_stderr(cmd, lines)

                async def reported_exit(exit_code: int) -> None:
                    pass

                label = "simulation_prepare"
            else:

                async def started_cb() -> None:
                    await cbs.simulator_prepare_started(sim, cmd)

                async def stdout_cb(lines: list[str]) -> None:
                    await cbs.simulator_prepare_stdout(sim, lines)

                async def stderr_cb(lines: list[str]) -> None:
                    await cbs.simulator_prepare_stderr(sim, lines)

                async def reported_exit(exit_code: int) -> None:
                    await cbs.simulator_prepare_exited(sim, exit_code)

                label = sim.full_name()

            async def exited_cb(exit_code: int) -> None:
                await reported_exit(exit_code)
                if exit_code != 0:
                    raise RuntimeError(f"prepare command failed with exit code {exit_code}: {cmd}")

            executor = CommandExecutor(
                cmd, label, started_cb, exited_cb, stdout_cb, stderr_cb, self.message
            )
            await executor.start()
            await executor.wait()

    async def start_simulator(self, sim: sim_base.Simulator, cmd) -> CommandExecutor:
        async def started_cb() -> None:
            await self._sim_exec_cbs.simulator_started(sim, cmd)

        async def exited_cb(exit_code: int) -> None:
            await self._sim_exec_cbs.simulator_exited(sim, exit_code)

        async def stdout_cb(lines: list[str]) -> None:
            await self._sim_exec_cbs.simulator_stdout(sim, lines)

        async def stderr_cb(lines: list[str]) -> None:
            await self._sim_exec_cbs.simulator_stderr(sim, lines)

        executor = CommandExecutor(
            cmd, sim.full_name(), started_cb, exited_cb, stdout_cb, stderr_cb, self.message
        )
        await executor.start()
        return executor

    async def start_proxy(self, proxy: inst_proxy.Proxy, cmd) -> CommandExecutor:
        async def started_cb() -> None:
            await self._sim_exec_cbs.proxy_started(proxy, cmd)

        async def exited_cb(exit_code: int) -> None:
            await self._sim_exec_cbs.proxy_exited(proxy, exit_code)

        async def stdout_cb(lines: list[str]) -> None:
            await self._sim_exec_cbs.proxy_stdout(proxy, lines)

        async def stderr_cb(lines: list[str]) -> None:
            await self._sim_exec_cbs.proxy_stderr(proxy, lines)

        executor = CommandExecutor(
            cmd, proxy.name, started_cb, exited_cb, stdout_cb, stderr_cb, self.message
        )
        await executor.start()
        return executor
