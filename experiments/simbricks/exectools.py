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

import asyncio
import shlex
import os
import signal

class HostConfig(object):
    def __init__(self, name, ip, mac, sudopwd, other={}):
        self.name = name
        self.ip = ip
        self.used_ip = ip
        self.mac = mac
        self.sudo_pwd = sudopwd
        self.other = other.copy()

class Component(object):
    def __init__(self, cmd_parts, with_stdin=False):
        self.is_ready = False
        self.stdout = []
        self.stdout_buf = bytearray()
        self.stderr = []
        self.stderr_buf = bytearray()
        self.cmd_parts = cmd_parts
        #print(cmd_parts)
        self.with_stdin = with_stdin

    def _parse_buf(self, buf, data):
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

    async def _consume_out(self, data):
        eof = len(data) == 0
        ls = self._parse_buf(self.stdout_buf, data)
        if len(ls) > 0 or eof:
            await self.process_out(ls, eof=eof)
            self.stdout = self.stdout + ls

    async def _consume_err(self, data):
        eof = len(data) == 0
        ls = self._parse_buf(self.stderr_buf, data)
        if len(ls) > 0 or eof:
            await self.process_err(ls, eof=eof)
            self.stderr = self.stderr + ls

    async def _read_stream(self, stream, fn):
        while True:
            bs = await stream.readline()
            if bs:
                await fn(bs)
            else:
                await fn(bs)
                return

    async def _waiter(self):
        out_handlers = asyncio.ensure_future(asyncio.wait([
            self._read_stream(self.proc.stdout, self._consume_out),
            self._read_stream(self.proc.stderr, self._consume_err)]))
        rc = await self.proc.wait()
        await out_handlers
        await self.terminated(rc)
        return rc

    async def send_input(self, bs, eof=False):
        self.proc.stdin.write(bs)
        if eof:
            self.proc.stdin.close()

    async def start(self):
        if self.with_stdin:
            stdin = asyncio.subprocess.PIPE
        else:
            stdin = None

        self.proc = await asyncio.create_subprocess_exec(*self.cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=stdin,
                )
        self.terminate_future = asyncio.ensure_future(self._waiter())
        await self.started()

    async def wait(self):
        await self.terminate_future

    async def interrupt(self):
        if self.terminate_future.done():
            return
        self.proc.send_signal(signal.SIGINT)

    async def terminate(self):
        if self.terminate_future.done():
            return
        self.proc.terminate()

    async def kill(self):
        self.proc.kill()

    async def int_term_kill(self, delay=5):
        await self.interrupt()
        _,pending = await asyncio.wait([self.terminate_future], timeout=delay)
        if len(pending) != 0:
            print('terminating')
            await self.terminate()
            _,pending = await asyncio.wait([self.terminate_future],
                    timeout=delay)
            if len(pending) != 0:
                print('killing')
                await self.kill()

    async def started(self):
        pass

    async def terminated(self, rc):
        pass

    async def process_out(self, lines, eof):
        pass

    async def process_err(self, lines, eof):
        pass

class RemoteComp(Component):
    def __init__(self, host, cmd_parts, cwd=None, **kwargs):
        if cwd is not None:
            cmd_parts = ['cd', cwd, '&&',
                    '(' + (' '.join(map(shlex.quote, cmd_parts))) + ')']
        parts = [
            'ssh',
            '-o',
            'UserKnownHostsFile=/dev/null',
            '-o',
            'StrictHostKeyChecking=no',
            host.name,
            '--'] + cmd_parts
        #print(parts)
        super().__init__(parts, **kwargs)


class SimpleComponent(Component):
    def __init__(self, label, cmd_parts, verbose=True, canfail=False,
            *args, **kwargs):
        self.label = label
        self.verbose = verbose
        self.canfail = canfail
        self.cmd_parts = cmd_parts
        super().__init__(cmd_parts, *args, **kwargs)

    async def process_out(self, lines, eof):
        if self.verbose:
            for l in lines:
                print(self.label, 'OUT:', lines, flush=True)

    async def process_err(self, lines, eof):
        if self.verbose:
            for l in lines:
                print(self.label, 'ERR:', lines, flush=True)

    async def terminated(self, rc):
        if self.verbose:
            print(self.label, 'TERMINATED:', rc, flush=True)
        if not self.canfail and rc != 0:
            raise Exception('Command Failed: ' + str(self.cmd_parts))


# runs the list of commands as strings sequentially
async def run_cmdlist(label, cmds, verbose=True):
    i = 0
    for cmd in cmds:
        cmdC = SimpleComponent(label + '.' + str(i), shlex.split(cmd),
                verbose=verbose)
        await cmdC.start()
        await cmdC.wait()

async def await_file(path, delay=0.05, verbose=False):
    if verbose:
        print('await_file(%s)' % path)
    while not os.path.exists(path):
        await asyncio.sleep(delay)
