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
The main runner's part of a run stream: its websocket to the backend, relayed
into the executor's mux message by message.

The runner never looks inside a stream beyond the op byte. It keeps the
websocket up for as long as the stream lives: a dropped connection is retried
with the same ticket, which the backend accepts for the stream's whole life,
and the ends' sequence numbers sort out the frame that may arrive twice after
that. A close with code 1000 is the backend saying the run ended.
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from simbricks.client.streams import protocol
from simbricks.client.streams.protocol import Op
from simbricks.runner import streams as runner_streams

LOGGER = logging.getLogger(__name__)

_RECONNECT_DELAY_SEC = (0.5, 1, 2, 5, 10)
_MAX_MESSAGE = 16 << 20


class StreamBridge:
    def __init__(self, stream_id: bytes, url: str, streams: runner_streams.StreamChannel) -> None:
        self.stream_id = stream_id
        self._url = url
        self._streams = streams
        #: Messages from the executor waiting for the websocket; bounded so an
        #: absent backend backpressures the executor instead of filling memory.
        self._to_ws: asyncio.Queue[bytes] = asyncio.Queue(maxsize=16)
        #: Set once the executor ended the stream (CLOSE or REJECT went out).
        self._ended = asyncio.Event()
        self.task: asyncio.Task | None = None

    def start(self) -> None:
        self.task = asyncio.create_task(self._run(), name=f"stream-{self.stream_id.hex()[:8]}")

    async def on_message(self, message: bytes) -> None:
        """Executor → backend; the mux calls this."""
        await self._to_ws.put(message)

    async def stop(self, reason: str) -> None:
        """Give up on the stream from the runner's side, telling the executor why."""
        if self.task is not None and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except (asyncio.CancelledError, Exception):
                pass
        await self._close_executor_side(reason)

    async def _run(self) -> None:
        attempt = 0
        while not self._ended.is_set():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                        self._url, max_msg_size=_MAX_MESSAGE, heartbeat=20
                    ) as ws:
                        attempt = 0
                        code = await self._relay(ws)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                LOGGER.warning(f"stream {self.stream_id.hex()}: websocket failed: {error}")
                code = None

            if self._ended.is_set():
                return
            if code == aiohttp.WSCloseCode.OK:
                # the backend closes with 1000 only when the run is over
                await self._close_executor_side("run finished")
                return

            delay = _RECONNECT_DELAY_SEC[min(attempt, len(_RECONNECT_DELAY_SEC) - 1)]
            attempt += 1
            LOGGER.info(f"stream {self.stream_id.hex()}: reconnecting in {delay}s")
            await asyncio.sleep(delay)

    async def _relay(self, ws: aiohttp.ClientWebSocketResponse) -> int | None:
        """Pump both directions until the socket closes or the executor ends the stream."""
        from_ws = asyncio.create_task(self._ws_to_executor(ws))
        to_ws = asyncio.create_task(self._executor_to_ws(ws))
        try:
            done, _ = await asyncio.wait({from_ws, to_ws}, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            for task in (from_ws, to_ws):
                task.cancel()
            if not ws.closed:
                await ws.close()
        return ws.close_code

    async def _ws_to_executor(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        async for message in ws:
            if message.type is aiohttp.WSMsgType.BINARY:
                data = message.data
            elif message.type is aiohttp.WSMsgType.TEXT:
                data = message.data.encode("utf-8")
            else:
                continue
            try:
                await self._streams.send(self.stream_id, data)
            except RuntimeError:
                # the executor closed the stream from its side already
                return

    async def _executor_to_ws(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        while True:
            message = await self._to_ws.get()
            await ws.send_bytes(message)
            op = Op(message[0])
            if op is Op.DATA:
                # delivered to the backend: the executor may send that much again
                self._streams.consumed(self.stream_id, len(message) - 5)
            elif op in (Op.CLOSE, Op.REJECT):
                self._ended.set()
                return

    async def _close_executor_side(self, reason: str) -> None:
        if self.stream_id not in self._streams:
            return
        close = protocol.encode_model(Op.CLOSE, protocol.Close(reason=reason))
        try:
            await self._streams.send(self.stream_id, close)
        except Exception:
            LOGGER.debug(f"stream {self.stream_id.hex()}: executor unreachable while closing")
