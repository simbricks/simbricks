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
What clients typically do with run streams: forward ports and read files.

``forward_tcp`` is ``ssh -L``: a local port whose connections become streams
to a ``connect`` target inside the executor. ``reverse_tcp`` is ``ssh -R``: a
``listen`` target inside the executor whose connections are served by
connecting out locally. ``read_file`` streams a file from the run's work
directory, optionally following it as it grows.
"""

from __future__ import annotations

import asyncio
import logging
import typing

from simbricks.client.namespace import StreamCreated
from simbricks.client.streams.bridge import bridge
from simbricks.client.streams.session import RunStreams, params_of
from simbricks.client.streams.stream import Stream, StreamClosed

LOGGER = logging.getLogger(__name__)


async def forward_tcp(
    streams: RunStreams, run_fragment_id: str, local_host: str, local_port: int, target: str
) -> asyncio.base_events.Server:
    """Listen locally; every accepted connection becomes a stream to ``target``."""

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        stream = await streams.open(run_fragment_id, target)
        try:
            await stream.wait_accepted()
        except StreamClosed as error:
            LOGGER.error(f"forward to {target} refused: {error.reason}")
            writer.close()
            return
        await bridge(stream, reader, writer)

    server = await asyncio.start_server(handle, local_host, local_port)
    LOGGER.info(f"forwarding {local_host}:{local_port} -> {target}")
    return server


async def reverse_tcp(
    streams: RunStreams, run_fragment_id: str, target: str, local_host: str, local_port: int
) -> Stream:
    """
    Make the executor listen (``target`` is a ``listen`` target); every
    connection it accepts is served by connecting to ``local_host:local_port``.

    The first connection rides on the returned stream; further ones arrive as
    executor-opened streams, which :meth:`RunStreams.watch` must be running to
    pick up (see :func:`serve_reverse_connections`).
    """
    stream = await streams.open(run_fragment_id, target)
    info = (await stream.wait_accepted()).info
    LOGGER.info(f"executor listening at {info}, serving from {local_host}:{local_port}")

    async def first_connection() -> None:
        try:
            await stream.wait_peer()
            reader, writer = await asyncio.open_connection(local_host, local_port)
        except StreamClosed:
            return
        except OSError as error:
            await stream.close(f"local connect failed: {error}")
            return
        await bridge(stream, reader, writer)

    asyncio.create_task(first_connection())
    return stream


def serve_reverse_connections(
    listener_target: str, local_host: str, local_port: int
) -> tuple[
    typing.Callable[[StreamCreated], bool],
    typing.Callable[[StreamCreated, Stream], typing.Awaitable[None]],
]:
    """The ``accept`` and ``on_stream`` pair for :meth:`RunStreams.watch` behind a reverse forward."""

    def accept(event: StreamCreated) -> bool:
        return event.target == listener_target and "listener" in params_of(event)

    async def on_stream(event: StreamCreated, stream: Stream) -> None:
        try:
            reader, writer = await asyncio.open_connection(local_host, local_port)
        except OSError as error:
            await stream.close(f"local connect failed: {error}")
            return
        asyncio.create_task(bridge(stream, reader, writer))

    return accept, on_stream


async def read_file(
    streams: RunStreams,
    run_fragment_id: str,
    path: str,
    sink: typing.Callable[[bytes], typing.Awaitable[None]],
    follow: bool = False,
) -> None:
    """Stream a file from the run's work directory into ``sink`` until EOF (or forever with ``follow``)."""
    stream = await streams.open(run_fragment_id, f"file:read:{path}", {"follow": follow})
    await stream.wait_accepted()
    try:
        while data := await stream.read():
            await sink(data)
    except StreamClosed as error:
        if error.reason not in ("", "eof"):
            raise
    finally:
        await stream.close("done")
