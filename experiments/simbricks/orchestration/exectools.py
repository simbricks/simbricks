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

import abc
import asyncio
import os
import pathlib
import re
import shlex
import shutil
import signal
import typing as tp
from asyncio.subprocess import Process


class Component(object):

    def __init__(self, cmd_parts: tp.List[str], with_stdin=False):
        self.is_ready = False
        self.stdout: tp.List[str] = []
        self.stdout_buf = bytearray()
        self.stderr: tp.List[str] = []
        self.stderr_buf = bytearray()
        self.cmd_parts = cmd_parts
        #print(cmd_parts)
        self.with_stdin = with_stdin

        self._proc: Process
        self._terminate_future: asyncio.Task

    def _parse_buf(self, buf: bytearray, data: bytes) -> tp.List[str]:
        if data is not None:
            buf.extend(data)
        lines = []
        start = 0
        for i in range(0, len(buf)):
            if buf[i] == ord('\n'):
                l = buf[start:i].decode('utf-8')
                lines.append(l)
                start = i + 1
        del buf[0:start]

        if len(data) == 0 and len(buf) > 0:
            lines.append(buf.decode('utf-8'))
        return lines

    async def _consume_out(self, data: bytes) -> None:
        eof = len(data) == 0
        ls = self._parse_buf(self.stdout_buf, data)
        if len(ls) > 0 or eof:
            await self.process_out(ls, eof=eof)
            self.stdout.extend(ls)

    async def _consume_err(self, data: bytes) -> None:
        eof = len(data) == 0
        ls = self._parse_buf(self.stderr_buf, data)
        if len(ls) > 0 or eof:
            await self.process_err(ls, eof=eof)
            self.stderr.extend(ls)

    async def _read_stream(self, stream: asyncio.StreamReader, fn):
        while True:
            bs = await stream.readline()
            if bs:
                await fn(bs)
            else:
                await fn(bs)
                return

    async def _waiter(self) -> None:
        stdout_handler = asyncio.create_task(
            self._read_stream(self._proc.stdout, self._consume_out)
        )
        stderr_handler = asyncio.create_task(
            self._read_stream(self._proc.stderr, self._consume_err)
        )
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
            print(
                f'terminating component {self.cmd_parts[0]} '
                f'pid {self._proc.pid}',
                flush=True
            )
            await self.terminate()

        try:
            await asyncio.wait_for(self._proc.wait(), delay)
            return
        except (TimeoutError, asyncio.TimeoutError):
            print(
                f'killing component {self.cmd_parts[0]} '
                f'pid {self._proc.pid}',
                flush=True
            )
            await self.kill()
        await self._proc.wait()

    async def started(self) -> None:
        pass

    async def terminated(self, rc: int) -> None:
        pass

    async def process_out(self, lines: tp.List[str], eof: bool) -> None:
        pass

    async def process_err(self, lines: tp.List[str], eof: bool) -> None:
        pass


class SimpleComponent(Component):

    def __init__(
        self,
        label: str,
        cmd_parts: tp.List[str],
        *args,
        verbose=True,
        canfail=False,
        **kwargs
    ) -> None:
        self.label = label
        self.verbose = verbose
        self.canfail = canfail
        self.cmd_parts = cmd_parts
        super().__init__(cmd_parts, *args, **kwargs)

    async def process_out(self, lines: tp.List[str], eof: bool) -> None:
        if self.verbose:
            for _ in lines:
                print(self.label, 'OUT:', lines, flush=True)

    async def process_err(self, lines: tp.List[str], eof: bool) -> None:
        if self.verbose:
            for _ in lines:
                print(self.label, 'ERR:', lines, flush=True)

    async def terminated(self, rc: int) -> None:
        if self.verbose:
            print(self.label, 'TERMINATED:', rc, flush=True)
        if not self.canfail and rc != 0:
            raise RuntimeError('Command Failed: ' + str(self.cmd_parts))


class SimpleRemoteComponent(SimpleComponent):

    def __init__(
        self,
        host_name: str,
        label: str,
        cmd_parts: tp.List[str],
        *args,
        cwd: tp.Optional[str] = None,
        ssh_extra_args: tp.Optional[tp.List[str]] = None,
        **kwargs
    ) -> None:
        if ssh_extra_args is None:
            ssh_extra_args = []

        self.host_name = host_name
        self.extra_flags = ssh_extra_args
        # add a wrapper to print the PID
        remote_parts = ['echo', 'PID', '$$', '&&']

        if cwd is not None:
            # if necessary add a CD command
            remote_parts += ['cd', cwd, '&&']

        # escape actual command parts
        cmd_parts = list(map(shlex.quote, cmd_parts))

        # use exec to make sure the command we run keeps the PIDS
        remote_parts += ['exec'] + cmd_parts

        # wrap up command in ssh invocation
        parts = self._ssh_cmd(remote_parts)

        super().__init__(label, parts, *args, **kwargs)

        self._pid_fut: tp.Optional[asyncio.Future] = None

    def _ssh_cmd(self, parts: tp.List[str]) -> tp.List[str]:
        """SSH invocation of command for this host."""
        return [
            'ssh',
            '-o',
            'UserKnownHostsFile=/dev/null',
            '-o',
            'StrictHostKeyChecking=no'
        ] + self.extra_flags + [self.host_name, '--'] + parts

    async def start(self) -> None:
        """Start this command (includes waiting for its pid)."""
        self._pid_fut = asyncio.get_running_loop().create_future()
        await super().start()
        await self._pid_fut

    async def process_out(self, lines: tp.List[str], eof: bool) -> None:
        """Scans output and set PID future once PID line found."""
        if not self._pid_fut.done():
            newlines = []
            pid_re = re.compile(r'^PID\s+(\d+)\s*$')
            for l in lines:
                m = pid_re.match(l)
                if m:
                    pid = int(m.group(1))
                    self._pid_fut.set_result(pid)
                else:
                    newlines.append(l)
            lines = newlines

            if eof and not self._pid_fut.done():
                # cancel PID future if it's not going to happen
                print('PID not found but EOF already found:', self.label)
                self._pid_fut.cancel()
        await super().process_out(lines, eof)

    async def _kill_cmd(self, sig: str) -> None:
        """Send signal to command by running ssh kill -$sig $PID."""
        cmd_parts = self._ssh_cmd([
            'kill', '-' + sig, str(self._pid_fut.result())
        ])
        proc = await asyncio.create_subprocess_exec(*cmd_parts)
        await proc.wait()

    async def interrupt(self) -> None:
        await self._kill_cmd('INT')

    async def terminate(self) -> None:
        await self._kill_cmd('TERM')

    async def kill(self) -> None:
        await self._kill_cmd('KILL')


class Executor(abc.ABC):

    def __init__(self) -> None:
        self.ip = None

    @abc.abstractmethod
    def create_component(
        self, label: str, parts: tp.List[str], **kwargs
    ) -> SimpleComponent:
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
    async def run_cmdlist(
        self, label: str, cmds: tp.List[str], verbose=True
    ) -> None:
        i = 0
        for cmd in cmds:
            cmd_c = self.create_component(
                label + '.' + str(i), shlex.split(cmd), verbose=verbose
            )
            await cmd_c.start()
            await cmd_c.wait()

    async def await_files(self, paths: tp.List[str], *args, **kwargs) -> None:
        xs = []
        for p in paths:
            waiter = asyncio.create_task(self.await_file(p, *args, **kwargs))
            xs.append(waiter)

        await asyncio.gather(*xs)


class LocalExecutor(Executor):

    def create_component(
        self, label: str, parts: tp.List[str], **kwargs
    ) -> SimpleComponent:
        return SimpleComponent(label, parts, **kwargs)

    async def await_file(
        self, path: str, delay=0.05, verbose=False, timeout=30
    ) -> None:
        if verbose:
            print(f'await_file({path})')
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


class RemoteExecutor(Executor):

    def __init__(self, host_name: str, workdir: str) -> None:
        super().__init__()

        self.host_name = host_name
        self.cwd = workdir
        self.ssh_extra_args = []
        self.scp_extra_args = []

    def create_component(
        self, label: str, parts: tp.List[str], **kwargs
    ) -> SimpleRemoteComponent:
        return SimpleRemoteComponent(
            self.host_name,
            label,
            parts,
            cwd=self.cwd,
            ssh_extra_args=self.ssh_extra_args,
            **kwargs
        )

    async def await_file(
        self, path: str, delay=0.05, verbose=False, timeout=30
    ) -> None:
        if verbose:
            print(f'{self.host_name}.await_file({path}) started')

        to_its = int(timeout / delay)
        loop_cmd = (
            f'i=0 ; while [ ! -e {path} ] ; do '
            f'if [ $i -ge {to_its} ] ; then exit 1 ; fi ; '
            f'sleep {delay} ; '
            'i=$(($i+1)) ; done; exit 0'
        )
        parts = ['/bin/sh', '-c', loop_cmd]
        sc = self.create_component(
            f"{self.host_name}.await_file('{path}')",
            parts,
            canfail=False,
            verbose=verbose
        )
        await sc.start()
        await sc.wait()

    # TODO: Implement opitimized await_files()

    async def send_file(self, path: str, verbose=False) -> None:
        parts = [
            'scp',
            '-o',
            'UserKnownHostsFile=/dev/null',
            '-o',
            'StrictHostKeyChecking=no'
        ] + self.scp_extra_args + [path, f'{self.host_name}:{path}']
        sc = SimpleComponent(
            f'{self.host_name}.send_file("{path}")',
            parts,
            canfail=False,
            verbose=verbose
        )
        await sc.start()
        await sc.wait()

    async def mkdir(self, path: str, verbose=False) -> None:
        sc = self.create_component(
            f"{self.host_name}.mkdir('{path}')", ['mkdir', '-p', path],
            canfail=False,
            verbose=verbose
        )
        await sc.start()
        await sc.wait()

    async def rmtree(self, path: str, verbose=False) -> None:
        sc = self.create_component(
            f'{self.host_name}.rmtree("{path}")', ['rm', '-rf', path],
            canfail=False,
            verbose=verbose
        )
        await sc.start()
        await sc.wait()
