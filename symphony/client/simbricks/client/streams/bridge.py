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


"""Pumping a socket and a stream into each other, as both ends of a port forward do."""

from __future__ import annotations

import asyncio

from simbricks.client.streams.stream import Stream, StreamClosed

#: Bytes read from a socket per stream write; matches the protocol's chunk size.
READ_SIZE = 64 * 1024


async def bridge(
    stream: Stream, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """
    Pump a socket and a stream into each other until both are done.

    Either side's EOF is passed on as a half-close; the stream is closed once
    both directions ended, or right away when either side breaks.
    """

    async def socket_to_stream() -> None:
        while data := await reader.read(READ_SIZE):
            await stream.write(data)
        await stream.write_eof()

    async def stream_to_socket() -> None:
        while data := await stream.read():
            writer.write(data)
            await writer.drain()
        if writer.can_write_eof():
            writer.write_eof()

    tasks = [asyncio.create_task(socket_to_stream()), asyncio.create_task(stream_to_socket())]
    try:
        await asyncio.gather(*tasks)
        await stream.close("eof")
    except StreamClosed:
        pass
    except Exception as error:
        await stream.close(f"socket error: {error}")
    finally:
        for task in tasks:
            task.cancel()
        writer.close()
