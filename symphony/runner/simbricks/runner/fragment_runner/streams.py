# MIT License
#
# Copyright (c) 2026 SimBricks
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""
What run streams connect to inside a fragment executor.

A stream's ``target`` names a socket the executor connects to or listens on,
or a file in the run's work directory; the executor bridges that to the stream.
``connect`` targets exist for simulators that listen (a guest's forwarded ssh
port, a gdb stub); ``listen`` targets for simulators that can only connect out
(a serial console pointed at a unix socket). A listening target carries its
first connection on the stream that created it and opens a new,
executor-initiated stream for every further connection, so a client can keep
serving them like ``ssh -R`` does. ``file:read`` streams a file out, following
it as it grows if asked, which is how a simulator's verbose debug log reaches a
client without ever being persisted.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import pathlib
import typing
import uuid

from simbricks.client.streams.bridge import bridge
from simbricks.client.streams.protocol import Open
from simbricks.client.streams.stream import Stream, StreamClosed
from simbricks.runner import streams as runner_streams

LOGGER = logging.getLogger(__name__)

#: How long an executor-initiated stream waits for a client before giving up
#: on the connection it was opened for.
ACCEPT_TIMEOUT_SEC = 30.0

#: Bytes read from a file per stream write; matches the protocol's chunk size.
READ_SIZE = 64 * 1024

#: How often a followed file is checked for growth.
FOLLOW_POLL_SEC = 0.2


@dataclasses.dataclass(frozen=True)
class Target:
    scheme: typing.Literal["tcp", "unix", "file"]
    mode: typing.Literal["connect", "listen", "read"]
    host: str
    port: int
    path: str

    @classmethod
    def parse(cls, target: str) -> Target:
        """
        ``tcp:connect:<host>:<port>``, ``tcp:listen:<addr>:<port>``,
        ``unix:connect:<path>``, ``unix:listen:<path>`` or ``file:read:<path>``.
        """
        scheme, _, rest = target.partition(":")
        mode, _, rest = rest.partition(":")
        match scheme:
            case "tcp" | "unix" if mode not in ("connect", "listen"):
                raise ValueError(f"unknown mode in target {target!r}, expected connect or listen")
            case "tcp":
                host, _, port = rest.rpartition(":")
                if not host or not port.isdigit():
                    raise ValueError(f"tcp target {target!r} needs <host>:<port>")
                return cls("tcp", mode, host, int(port), "")
            case "unix":
                if not rest:
                    raise ValueError(f"unix target {target!r} needs a path")
                return cls("unix", mode, "", 0, rest)
            case "file":
                if mode != "read":
                    raise ValueError(f"unknown mode in target {target!r}, expected read")
                if not rest:
                    raise ValueError(f"file target {target!r} needs a path")
                return cls("file", "read", "", 0, rest)
            case _:
                raise ValueError(f"unknown scheme in target {target!r}")


def resolve_in(workdir: pathlib.Path, path: str) -> pathlib.Path:
    """A path relative to the run's work directory, refusing to leave it."""
    resolved = (workdir / path).resolve()
    if not resolved.is_relative_to(workdir.resolve()):
        raise ValueError(f"{path!r} is outside the run's work directory")
    return resolved


async def serve_file(stream: Stream, path: pathlib.Path, follow: bool) -> None:
    """
    Stream a file out; with ``follow``, wait for it to appear and keep sending
    what gets appended until the stream is closed.
    """
    while not path.exists():
        if not follow:
            await stream.reject(f"{path} does not exist")
            return
        await asyncio.sleep(FOLLOW_POLL_SEC)
    await stream.accept({"path": str(path)})
    await stream.hello()

    closed = asyncio.create_task(stream.closed.wait())
    try:
        with path.open("rb") as file:
            while not stream.closed.is_set():
                data = file.read(READ_SIZE)
                if data:
                    await stream.write(data)
                    continue
                if not follow:
                    await stream.write_eof()
                    await stream.close("eof")
                    return
                await asyncio.wait({closed}, timeout=FOLLOW_POLL_SEC)
    except StreamClosed:
        pass
    except OSError as error:
        await stream.close(f"file error: {error}")
    finally:
        closed.cancel()


class Listener:
    """A listening target: bound once, feeding connections into streams."""

    def __init__(self, manager: StreamManager, target: Target, open_msg: Open, first: Stream):
        self._manager = manager
        self._target = target
        self._open = open_msg
        #: The stream that asked for the listener, waiting for the first connection.
        self._first: Stream | None = first
        self._server: asyncio.base_events.Server | None = None
        self._bridges: set[asyncio.Task] = set()

    async def start(self) -> dict[str, typing.Any]:
        """Bind; returns what to tell the client in ACCEPT."""
        target = self._target
        if target.scheme == "tcp":
            self._server = await asyncio.start_server(self._accepted, target.host, target.port)
            host, port = self._server.sockets[0].getsockname()[:2]
            return {"host": host, "port": port}
        self._server = await asyncio.start_unix_server(self._accepted, target.path)
        return {"path": target.path}

    def _accepted(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if self._first is not None:
            stream, self._first = self._first, None
            self._track(bridge(stream, reader, writer))
            return
        self._track(self._serve_extra(reader, writer))

    async def _serve_extra(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """A further connection: opens its own stream and waits for a client to take it."""
        stream = await self._manager.open_outgoing(
            self._open.run_id,
            self._open.run_fragment_id,
            self._open.target,
            {"listener": self._manager.stream_id_of(self)},
        )
        try:
            await asyncio.wait_for(stream.wait_peer(), ACCEPT_TIMEOUT_SEC)
        except (StreamClosed, TimeoutError, asyncio.TimeoutError):
            await stream.close("no client attached in time")
            writer.close()
            return
        await bridge(stream, reader, writer)

    def _track(self, coroutine: typing.Coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self._bridges.add(task)
        task.add_done_callback(self._bridges.discard)

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
        for task in list(self._bridges):
            task.cancel()


class StreamManager:
    """
    The streams of one fragment executor, keyed by the run they belong to.

    Owns the mux over the runner connection: incoming OPENs are resolved to a
    target here, and listeners open outgoing streams through here.
    """

    def __init__(self, channel: runner_streams.StreamChannel | None = None) -> None:
        self.channel = channel
        self._runs: dict[str, _RunStreams] = {}
        self._listeners: dict[int, bytes] = {}

    def attach(self, channel: runner_streams.StreamChannel) -> None:
        self.channel = channel

    def register_run(self, run_id: str, workdir: pathlib.Path) -> None:
        """File targets of this run resolve inside ``workdir``."""
        self._runs.setdefault(run_id, _RunStreams()).workdir = workdir

    def stream_id_of(self, listener: Listener) -> str:
        return self._listeners[id(listener)].hex()

    async def on_open(
        self, stream_id: bytes, open_msg: Open
    ) -> typing.Callable[[bytes], typing.Awaitable[None]] | None:
        """Resolve an OPEN from the runner; the mux calls this."""
        assert self.channel is not None
        stream = Stream(self.channel.transport(stream_id), "executor")
        run = self._runs.setdefault(open_msg.run_id, _RunStreams())
        run.track(self._serve(stream_id, open_msg, stream, run))
        return stream.feed

    async def open_outgoing(
        self, run_id: str, run_fragment_id: str, target: str, params: dict
    ) -> Stream:
        """Open a stream towards the runner, for a connection the executor accepted."""
        assert self.channel is not None
        stream_id = uuid.uuid4().bytes
        stream = Stream(self.channel.transport(stream_id), "executor")
        await self.channel.open(stream_id, target, run_id, run_fragment_id, params, stream.feed)
        await stream.hello()
        return stream

    async def close_run(self, run_id: str) -> None:
        """Tear down every stream and listener of a run that ended."""
        run = self._runs.pop(run_id, None)
        if run is not None:
            await run.close()

    async def close_all(self) -> None:
        for run_id in list(self._runs):
            await self.close_run(run_id)

    async def _serve(self, stream_id: bytes, open_msg: Open, stream: Stream, run: _RunStreams):
        try:
            target = Target.parse(open_msg.target)
        except ValueError as error:
            await stream.reject(str(error))
            return

        try:
            if target.scheme == "file":
                if run.workdir is None:
                    await stream.reject("run has no work directory here")
                    return
                path = resolve_in(run.workdir, target.path)
                await serve_file(stream, path, bool(open_msg.params.get("follow", False)))
                return

            if target.mode == "connect":
                if target.scheme == "tcp":
                    reader, writer = await asyncio.open_connection(target.host, target.port)
                    info = {"host": target.host, "port": target.port}
                else:
                    reader, writer = await asyncio.open_unix_connection(target.path)
                    info = {"path": target.path}
                await stream.accept(info)
                await stream.hello()
                await bridge(stream, reader, writer)
                return

            listener = Listener(self, target, open_msg, stream)
            info = await listener.start()
        except (OSError, ValueError) as error:
            await stream.reject(str(error))
            return

        self._listeners[id(listener)] = stream_id
        run.listeners.add(listener)
        try:
            await stream.accept(info)
            await stream.hello()
            # the listener lives exactly as long as the stream that asked for it
            await stream.closed.wait()
        finally:
            run.listeners.discard(listener)
            self._listeners.pop(id(listener), None)
            await listener.close()


class _RunStreams:
    def __init__(self) -> None:
        self.tasks: set[asyncio.Task] = set()
        self.listeners: set[Listener] = set()
        self.workdir: pathlib.Path | None = None

    def track(self, coroutine: typing.Coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def close(self) -> None:
        for listener in list(self.listeners):
            await listener.close()
        for task in list(self.tasks):
            task.cancel()
