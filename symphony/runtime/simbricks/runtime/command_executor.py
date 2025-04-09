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

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import proxy as inst_proxy
    from simbricks.orchestration.simulation import base as sim_base
    from simbricks.runtime import simulation_executor as sim_exec


class CommandExecutor:

    def __init__(
        self,
        cmd: str,
        label: str,
        started_callback: typing.Callable[[], typing.Awaitable[None]],
        exited_callback: typing.Callable[[int], typing.Awaitable[None]],
        stdout_callback: typing.Callable[[list[str]], typing.Awaitable[None]],
        stderr_callback: typing.Callable[[list[str]], typing.Awaitable[None]],
    ):
        self._stdout_buf = bytearray()
        self._stderr_buf = bytearray()
        self._cmd_parts = shlex.split(cmd)
        self._label = label
        self._started_cb = started_callback
        self._exited_cb = exited_callback
        self._stdout_cb = stdout_callback
        self._stderr_cb = stderr_callback

        self._proc: Process
        self._terminate_future: asyncio.Task

    def _parse_buf(self, buf: bytearray, data: bytes) -> list[str]:
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
        self, stream: asyncio.StreamReader, consume_fn: typing.Callable[[bytes], None]
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
            print(
                f"terminating component {self._cmd_parts[0]} pid" f" {self._proc.pid}",
                flush=True,
            )
            await self.terminate()

        try:
            await asyncio.wait_for(self._proc.wait(), delay)
            return
        except (TimeoutError, asyncio.TimeoutError):
            print(
                f"killing component {self._cmd_parts[0]} pid {self._proc.pid}",
                flush=True,
            )
            await self.kill()
        await self._proc.wait()

    async def sigusr1(self) -> None:
        """Sends an SIGUSR1 signal."""
        if self._proc.returncode is None:
            self._proc.send_signal(signal.SIGUSR1)


class CommandExecutorFactory:

    def __init__(self, sim_exec_cbs: sim_exec.SimulationExecutorCallbacks):
        self._sim_exec_cbs = sim_exec_cbs

    async def exec_generic_prepare_cmds(self, cmds: list[str]) -> None:
        for cmd in cmds:

            async def started_cb() -> None:
                await self._sim_exec_cbs.simulation_prepare_cmd_start(cmd)

            async def exited_cb(exit_code: int) -> None:
                if exit_code != 0:
                    raise RuntimeError(f"The following prepare command failed: {cmd}")

            async def stdout_cb(lines: list[str]) -> None:
                await self._sim_exec_cbs.simulation_prepare_cmd_stdout(cmd, lines)

            async def stderr_cb(lines: list[str]) -> None:
                await self._sim_exec_cbs.simulation_prepare_cmd_stderr(cmd, lines)

            executor = CommandExecutor(
                cmd, "simulation_prepare", started_cb, exited_cb, stdout_cb, stderr_cb
            )
            await executor.start()
            await executor.wait()

    async def exec_simulator_prepare_cmds(self, sim: sim_base.Simulator, cmds: list[str]) -> None:
        for cmd in cmds:

            async def started_cb() -> None:
                await self._sim_exec_cbs.simulator_prepare_started(sim, cmd)

            async def exited_cb(exit_code: int) -> None:
                await self._sim_exec_cbs.simulator_prepare_exited(sim, exit_code)

            async def stdout_cb(lines: list[str]) -> None:
                await self._sim_exec_cbs.simulator_prepare_stdout(sim, lines)

            async def stderr_cb(lines: list[str]) -> None:
                await self._sim_exec_cbs.simulator_prepare_stderr(sim, lines)

            executor = CommandExecutor(
                cmd, sim.full_name(), started_cb, exited_cb, stdout_cb, stderr_cb
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
            cmd, sim.full_name(), started_cb, exited_cb, stdout_cb, stderr_cb
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
            cmd, proxy.name, started_cb, exited_cb, stdout_cb, stderr_cb
        )
        await executor.start()
        return executor
