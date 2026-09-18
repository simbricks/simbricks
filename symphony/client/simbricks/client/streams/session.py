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
Opening run streams from a client and attaching to their websockets.

A stream is created with a REST call that returns the ticket URL for the
client's side; the websocket at that URL stays valid for the stream's whole
life, so a dropped connection is simply re-attached with a higher HELLO
attempt. Streams a fragment executor opened towards clients (a simulator
connected to a listener) show up as StreamCreated events from the run's
runners and are attached the same way.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import typing
from collections.abc import Awaitable, Callable

import aiohttp

from simbricks.client import namespace
from simbricks.client.namespace import SimBricksClient, StreamCreated
from simbricks.client.openapi.client.python.sim_bricks_api_client import types as api_types
from simbricks.client.streams.stream import Stream

LOGGER = logging.getLogger(__name__)

_RECONNECT_DELAY_SEC = (0.5, 1, 2, 5, 10)
_MAX_MESSAGE = 16 << 20


class _WebSocketTransport:
    """Sends on whatever socket is currently attached, waiting through reconnects."""

    def __init__(self) -> None:
        self.ws: aiohttp.ClientWebSocketResponse | None = None
        self.attached = asyncio.Event()

    async def send(self, message: bytes) -> None:
        await self.attached.wait()
        assert self.ws is not None
        await self.ws.send_bytes(message)

    def consumed(self, amount: int) -> None:
        pass


class AttachedStream:
    """A client-side :class:`Stream` kept attached to its websocket."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._transport = _WebSocketTransport()
        self.stream = Stream(self._transport, "client")
        self._attempt = 0
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def close(self, reason: str = "") -> None:
        await self.stream.close(reason)
        await asyncio.sleep(0)  # let the CLOSE go out before the socket does
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def _run(self) -> None:
        backoff = 0
        while not self.stream.closed.is_set():
            code: int | None = None
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                        self._url, max_msg_size=_MAX_MESSAGE, heartbeat=20
                    ) as ws:
                        backoff = 0
                        self._attempt += 1
                        self._transport.ws = ws
                        self._transport.attached.set()
                        await self.stream.hello(self._attempt)
                        async for message in ws:
                            if message.type is aiohttp.WSMsgType.BINARY:
                                await self.stream.feed(message.data)
                        code = ws.close_code
            except asyncio.CancelledError:
                raise
            except Exception as error:
                LOGGER.warning(f"stream websocket failed: {error}")
            finally:
                self._transport.attached.clear()
                self._transport.ws = None

            if self.stream.closed.is_set():
                return
            if code == aiohttp.WSCloseCode.OK:
                # the backend closes with 1000 only once the run is over
                self.stream._mark_closed("run finished")
                return
            delay = _RECONNECT_DELAY_SEC[min(backoff, len(_RECONNECT_DELAY_SEC) - 1)]
            backoff += 1
            LOGGER.info(f"stream websocket lost, reconnecting in {delay}s")
            await asyncio.sleep(delay)


class RunStreams:
    """The streams of one run, from the client's side."""

    def __init__(self, sbc: SimBricksClient, run_id: str) -> None:
        self._sbc = sbc
        self.run_id = run_id
        self._attached: list[AttachedStream] = []

    async def open(
        self, run_fragment_id: str, target: str, params: dict[str, typing.Any] | None = None
    ) -> Stream:
        """Open a stream to a fragment of the run; returns once attached (not yet accepted)."""
        created = await self._sbc.create_stream(self.run_id, run_fragment_id, target, params)
        assert isinstance(created.url, str)
        return await self.attach(created.url)

    async def attach(self, url: str) -> Stream:
        attached = AttachedStream(url)
        attached.start()
        self._attached.append(attached)
        return attached.stream

    async def close(self) -> None:
        for attached in self._attached:
            await attached.close()
        self._attached.clear()

    async def fragment_ids(self) -> list[str]:
        fragments = await self._sbc.get_all_run_fragments(self.run_id)
        assert isinstance(fragments.data, list)
        return [f.id for f in fragments.data if isinstance(f.id, str)]

    async def watch(
        self,
        on_stream: Callable[[StreamCreated, Stream], Awaitable[None]],
        accept: Callable[[StreamCreated], bool] = lambda _: True,
        poll_interval_sec: float = 2.0,
    ) -> None:
        """
        Attach to streams the run's executors open towards clients.

        Polls the from-runner events of every runner executing a fragment of the
        run for StreamCreated, hands accepted ones to ``on_stream`` attached.
        Runs until cancelled.
        """
        fragments = await self._sbc.get_all_run_fragments(self.run_id)
        assert isinstance(fragments.data, list)
        runner_ids = {f.runner_id for f in fragments.data if isinstance(f.runner_id, str)}
        seen: set[str] = set()
        after = datetime.datetime.now() - datetime.timedelta(seconds=poll_interval_sec)
        while True:
            for runner_id in runner_ids:
                events = await self._sbc.get_runner_events(runner_id, after=after)
                for event in events:
                    if not isinstance(event, StreamCreated) or event.run_id != self.run_id:
                        continue
                    if event.stream_id in seen or not accept(event):
                        continue
                    seen.add(event.stream_id)
                    if not isinstance(event.produced_at, api_types.Unset):
                        after = min(after, event.produced_at)
                    LOGGER.info(f"executor opened stream {event.stream_id} ({event.target})")
                    await on_stream(event, await self.attach(event.url))
            await asyncio.sleep(poll_interval_sec)


def params_of(event: StreamCreated) -> dict[str, typing.Any]:
    return {} if isinstance(event.params, api_types.Unset) else event.params.to_dict()


__all__ = ["AttachedStream", "RunStreams", "params_of", "namespace"]
