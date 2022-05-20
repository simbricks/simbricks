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
import os
import pathlib
import re
import shlex
import shutil
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

class SimpleRemoteComponent(SimpleComponent):
    def __init__(self, host_name, label, cmd_parts, cwd=None, *args, **kwargs):
        self.host_name = host_name
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

    def _ssh_cmd(self, parts):
        """ SSH invocation of command for this host. """
        return [
            'ssh',
            '-o',
            'UserKnownHostsFile=/dev/null',
            '-o',
            'StrictHostKeyChecking=no',
            self.host_name,
            '--'] + parts

    async def start(self):
        """ Start this command (includes waiting for its pid. """
        self.pid_fut = asyncio.get_running_loop().create_future()
        await super().start()
        await self.pid_fut

    async def process_out(self, lines, eof):
        """ Scans output and set PID future once PID line found. """
        if not self.pid_fut.done():
            newlines = []
            pid_re = re.compile(r'^PID\s+(\d+)\s*$')
            for l in lines:
                m = pid_re.match(l)
                if m:
                    pid = int(m.group(1))
                    self.pid_fut.set_result(pid)
                else:
                    newlines.append(l)
            lines = newlines

            if eof and not self.pid_fut.done():
                # cancel PID future if it's not going to happen
                print('PID not found but EOF already found:', self.label)
                self.pid_fut.cancel()
        await super().process_out(lines, eof)

    async def _kill_cmd(self, sig):
        """ Send signal to command by running ssh kill -$sig $PID. """
        cmd_parts = self._ssh_cmd(['kill', '-' + sig,
                str(self.pid_fut.result())])
        proc = await asyncio.create_subprocess_exec(*cmd_parts)
        await proc.wait()

    async def interrupt(self):
        await self._kill_cmd('INT')

    async def terminate(self):
        await self._kill_cmd('TERM')

    async def kill(self):
        await self._kill_cmd('KILL')

class Executor(object):
    ip = None

    def create_component(self, label, parts, **kwargs) -> SimpleComponent:
        raise NotImplementedError("Please Implement this method")

    async def await_file(self, path, delay=0.05, verbose=False):
        raise NotImplementedError("Please Implement this method")

    async def send_file(self, path, verbose=False):
        raise NotImplementedError("Please Implement this method")

    async def mkdir(self, path, verbose=False):
        raise NotImplementedError("Please Implement this method")

    async def rmtree(self, path, verbose=False):
        raise NotImplementedError("Please Implement this method")

    # runs the list of commands as strings sequentially
    async def run_cmdlist(self, label, cmds, verbose=True, host=None):
        i = 0
        for cmd in cmds:
            cmdC = self.create_component(label + '.' + str(i), shlex.split(cmd),
                    verbose=verbose)
            await cmdC.start()
            await cmdC.wait()

    async def await_files(self, paths, *args, **kwargs):
        xs = []
        for p in paths:
            xs.append(self.await_file(p, *args, **kwargs))
        await asyncio.wait(xs)

class LocalExecutor(Executor):
    def create_component(self, label, parts, **kwargs):
        return SimpleComponent(label, parts, **kwargs)

    async def await_file(self, path, delay=0.05, verbose=False, timeout=30):
        if verbose:
            print('await_file(%s)' % path)
        t = 0
        while not os.path.exists(path):
            if t >= timeout:
                raise TimeoutError()
            await asyncio.sleep(delay)
            t += delay

    async def send_file(self, path, verbose):
        # locally we do not need to do anything
        pass

    async def mkdir(self, path, verbose=False):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

    async def rmtree(self, path, verbose=False):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path):
            os.unlink(path)

class RemoteExecutor(Executor):
    def __init__(self, host_name, workdir):
        self.host_name = host_name
        self.cwd = workdir

    def create_component(self, label, parts, **kwargs):
        return SimpleRemoteComponent(self.host_name, label, parts,
                cwd=self.cwd, **kwargs)

    async def await_file(self, path, delay=0.05, verbose=False, timeout=30):
        if verbose:
            print('%s.await_file(%s) started' % (self.host_name, path))

        to_its = timeout / delay
        loop_cmd = ('i=0 ; while [ ! -e %s ] ; do '
                    'if [ $i -ge %u ] ; then exit 1 ; fi ; '
                    'sleep %f ; '
                    'i=$(($i+1)) ; done; exit 0') % (path, to_its, delay)
        parts = ['/bin/sh', '-c', loop_cmd]
        sc = self.create_component("%s.await_file('%s')" % (self.host_name,
                path), parts, canfail=False, verbose=verbose)
        await sc.start()
        await sc.wait()

    # TODO: Implement opitimized await_files()

    async def send_file(self, path, verbose):
        parts = [
            'scp',
            '-o',
            'UserKnownHostsFile=/dev/null',
            '-o',
            'StrictHostKeyChecking=no',
            path,
            '%s:%s' % (self.host_name, path)]
        sc = SimpleComponent("%s.send_file('%s')" % (
                self.host_name, path), parts, canfail=False, verbose=verbose)
        await sc.start()
        await sc.wait()

    async def mkdir(self, path, verbose=False):
        sc = self.create_component("%s.mkdir('%s')" % (self.host_name, path),
                ['mkdir', '-p', path], canfail=False, verbose=verbose)
        await sc.start()
        await sc.wait()

    async def rmtree(self, path, verbose=False):
        sc = self.create_component("%s.rmtree('%s')" % (self.host_name, path),
                ['rm', '-rf', path], canfail=False, verbose=verbose)
        await sc.start()
        await sc.wait()