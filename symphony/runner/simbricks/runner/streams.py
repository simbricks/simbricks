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
Run streams on the connection between a main runner and an executor.

The executor has no way to reach the backend, so the main runner attaches the
runner-side websocket of every stream and carries its messages over the frame
channel it already shares with the executor. Many streams share that one
channel next to events and artifacts, so each gets a credit window per
direction: a sender may only put as many DATA bytes on the channel as the
receiver granted, which keeps one stalled stream from blocking everything else
behind it. The relay legs on either side of the backend need no credit, one
websocket per stream gives them backpressure for free.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from simbricks.client.streams import protocol
from simbricks.client.streams.protocol import Op, Open
from simbricks.runner import framing

#: Credit each direction of a stream starts with, in DATA bytes.
DEFAULT_WINDOW = 1 << 20

#: Called with a stream id and the OPEN for it; returns the handler for that
#: stream's messages, or None to reject the stream.
OpenHandler = Callable[[bytes, Open], Awaitable[Callable[[bytes], Awaitable[None]] | None]]

_logger = logging.getLogger(__name__)


class _SendWindow:
    """Credit the peer granted us; senders wait here when it runs out."""

    def __init__(self, initial: int) -> None:
        self._available = initial
        self._changed = asyncio.Condition()

    async def acquire(self, amount: int) -> None:
        async with self._changed:
            await self._changed.wait_for(lambda: self._available >= amount)
            self._available -= amount

    async def grant(self, amount: int) -> None:
        async with self._changed:
            self._available += amount
            self._changed.notify_all()


class _ReceiveWindow:
    """Credit we granted the peer, and how much of it the consumer has freed again."""

    def __init__(self, window: int) -> None:
        self.window = window
        #: What the peer may still send before it must wait.
        self.allowance = window
        self._consumed = 0

    def received(self, amount: int) -> bool:
        """Account an arriving DATA payload; False if the peer overran its credit."""
        if amount > self.allowance:
            return False
        self.allowance -= amount
        return True

    def consumed(self, amount: int) -> int:
        """Account consumption; returns the credit to grant now, 0 if it can wait."""
        self._consumed += amount
        if self._consumed < self.window // 2:
            return 0
        grant, self._consumed = self._consumed, 0
        self.allowance += grant
        return grant


class _Entry:
    def __init__(self, window: int, on_message: Callable[[bytes], Awaitable[None]]) -> None:
        self.send = _SendWindow(window)
        self.receive = _ReceiveWindow(window)
        self.on_message = on_message


class _StreamTransport:
    """Adapts one stream of a channel to :class:`simbricks.client.streams.stream.Transport`."""

    def __init__(self, channel: StreamChannel, stream_id: bytes) -> None:
        self._channel = channel
        self._stream_id = stream_id

    async def send(self, message: bytes) -> None:
        await self._channel.send(self._stream_id, message)

    def consumed(self, amount: int) -> None:
        self._channel.consumed(self._stream_id, amount)


class StreamChannel:
    """
    All run streams multiplexed over one frame channel.

    Works on whole messages, not bytes: the main runner relays websocket
    messages through it unchanged, the executor wraps a stream's transport in a
    :class:`~simbricks.client.streams.stream.Stream`. Either peer may open a
    stream; the OPEN carries the initial window for both directions.
    """

    def __init__(
        self,
        channel: framing.FrameChannel,
        on_open: OpenHandler,
        window: int = DEFAULT_WINDOW,
    ) -> None:
        self._channel = channel
        self._on_open = on_open
        self._window = window
        self._entries: dict[bytes, _Entry] = {}

    def __contains__(self, stream_id: bytes) -> bool:
        return stream_id in self._entries

    def transport(self, stream_id: bytes) -> _StreamTransport:
        return _StreamTransport(self, stream_id)

    async def open(
        self,
        stream_id: bytes,
        target: str,
        run_id: str,
        run_fragment_id: str,
        params: dict | None,
        on_message: Callable[[bytes], Awaitable[None]],
    ) -> None:
        """Open a stream towards the peer; ``on_message`` receives what it sends back."""
        if stream_id in self._entries:
            raise RuntimeError(f"stream {stream_id.hex()} already open")
        self._entries[stream_id] = _Entry(self._window, on_message)
        message = protocol.encode_model(
            Op.OPEN,
            Open(
                target=target,
                run_id=run_id,
                run_fragment_id=run_fragment_id,
                params=params or {},
                window=self._window,
            ),
        )
        await self._channel.send(framing.StreamFrame.pack(stream_id, message))

    async def send(self, stream_id: bytes, message: bytes) -> None:
        """Send one end-to-end message on a stream, waiting for credit if it is DATA."""
        entry = self._entries.get(stream_id)
        if entry is None:
            raise RuntimeError(f"stream {stream_id.hex()} is not open")
        op, payload = protocol.decode(message)
        if op is Op.DATA:
            await entry.send.acquire(_data_bytes(payload))
        await self._channel.send(framing.StreamFrame.pack(stream_id, message))
        if op in (Op.CLOSE, Op.REJECT):
            self._entries.pop(stream_id, None)

    def consumed(self, stream_id: bytes, amount: int) -> None:
        """The consumer took ``amount`` DATA bytes off a stream; grants credit when due."""
        entry = self._entries.get(stream_id)
        if entry is None:
            return
        grant = entry.receive.consumed(amount)
        if grant:
            asyncio.create_task(
                self._channel.send(
                    framing.StreamFrame.pack(stream_id, protocol.encode_credit(grant))
                )
            )

    def forget(self, stream_id: bytes) -> None:
        """Drop a stream without telling the peer (it is gone already)."""
        self._entries.pop(stream_id, None)

    async def handle_frame(self, frame: framing.StreamFrame) -> None:
        """Dispatch one stream frame the peer sent."""
        stream_id, message = frame.unpack()
        op, payload = protocol.decode(message)

        if op is Op.OPEN:
            await self._handle_open(stream_id, Open.model_validate_json(payload))
            return

        entry = self._entries.get(stream_id)
        if entry is None:
            # closed from our side meanwhile, or never existed; either way nothing to do
            _logger.debug(f"dropping {op.name} for unknown stream {stream_id.hex()}")
            return

        match op:
            case Op.CREDIT:
                await entry.send.grant(protocol.decode_credit(payload))
            case Op.DATA:
                if not entry.receive.received(_data_bytes(payload)):
                    await self._protocol_error(stream_id, entry, "flow-control")
                    return
                await entry.on_message(message)
            case Op.CLOSE | Op.REJECT:
                self._entries.pop(stream_id, None)
                await entry.on_message(message)
            case _:
                await entry.on_message(message)

    async def close_all(self, reason: str) -> None:
        """Tell every open stream's handler the channel is gone; sends nothing."""
        entries, self._entries = self._entries, {}
        close = protocol.encode_model(Op.CLOSE, protocol.Close(reason=reason))
        for entry in entries.values():
            try:
                await entry.on_message(close)
            except Exception:
                _logger.debug("stream handler failed while closing", exc_info=True)

    async def _handle_open(self, stream_id: bytes, open_msg: Open) -> None:
        if stream_id in self._entries:
            await self._reject(stream_id, "stream id already in use")
            return
        on_message = await self._on_open(stream_id, open_msg)
        if on_message is None:
            await self._reject(stream_id, f"no handler for target {open_msg.target}")
            return
        self._entries[stream_id] = _Entry(open_msg.window, on_message)

    async def _reject(self, stream_id: bytes, reason: str) -> None:
        message = protocol.encode_model(Op.REJECT, protocol.Reject(reason=reason))
        await self._channel.send(framing.StreamFrame.pack(stream_id, message))

    async def _protocol_error(self, stream_id: bytes, entry: _Entry, reason: str) -> None:
        self._entries.pop(stream_id, None)
        close = protocol.encode_model(Op.CLOSE, protocol.Close(reason=reason))
        await self._channel.send(framing.StreamFrame.pack(stream_id, close))
        await entry.on_message(close)


def _data_bytes(payload: bytes) -> int:
    """What a DATA message costs in credit: its bytes without the sequence header."""
    return len(payload) - 4
