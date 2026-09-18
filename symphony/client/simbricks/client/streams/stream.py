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
The endpoint's view of one run stream.

A :class:`Stream` is what a port forwarder, a file writer or any other use case
reads from and writes to. It speaks :mod:`.protocol` over a transport its owner
provides (a websocket for the client, the runner frame channel for the fragment
executor) and is fed incoming messages by that owner.
"""

from __future__ import annotations

import asyncio
import typing

from simbricks.client.streams import protocol
from simbricks.client.streams.protocol import Accept, Close, Hello, Op, Reject


class StreamClosed(Exception):
    """The stream was closed deliberately, by either side."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason or "stream closed")
        self.reason = reason


class StreamRejected(StreamClosed):
    """The executor could not open the stream's target."""


class Transport(typing.Protocol):
    async def send(self, message: bytes) -> None:
        """Deliver one encoded message towards the peer."""
        ...

    def consumed(self, amount: int) -> None:
        """The application took ``amount`` bytes of DATA; legs with flow control grant credit here."""
        ...


class NullTransport:
    """A transport that goes nowhere, for tests and for streams already torn down."""

    async def send(self, message: bytes) -> None:
        pass

    def consumed(self, amount: int) -> None:
        pass


_EOF = object()
_CLOSED = object()


class Stream:
    """
    One end of a run stream.

    Reads return the peer's DATA in order and ``b""`` at its EOF; writes are
    chunked to :data:`protocol.MAX_DATA`. Inbound messages are queued up to
    ``inbound_limit`` DATA chunks, after which :meth:`feed` blocks — that is how
    backpressure reaches whatever feeds the stream.
    """

    def __init__(
        self,
        transport: Transport,
        side: typing.Literal["client", "executor"],
        inbound_limit: int = 64,
    ) -> None:
        self._transport = transport
        self.side: typing.Literal["client", "executor"] = side

        self._inbound: asyncio.Queue[typing.Any] = asyncio.Queue(maxsize=inbound_limit)
        self._send_seq = 0
        self._recv_seq = 0
        self._sent_eof = False
        self._received_eof = False

        loop = asyncio.get_running_loop()
        self._peer_hello: asyncio.Future[Hello] = loop.create_future()
        self.peer_reconnected = asyncio.Event()
        self._accepted: asyncio.Future[Accept] = loop.create_future()
        self._pong = asyncio.Event()

        self.closed = asyncio.Event()
        self.close_reason: str | None = None
        self._peer_closed = False

    # -- handshake -----------------------------------------------------------

    async def hello(self, attempt: int = 1) -> None:
        await self._send(protocol.encode_model(Op.HELLO, Hello(side=self.side, attempt=attempt)))

    async def wait_peer(self) -> Hello:
        """Wait for the peer's first HELLO (the relay holds it until both are attached)."""
        return await asyncio.shield(self._peer_hello)

    @property
    def peer(self) -> Hello | None:
        return self._peer_hello.result() if self._peer_hello.done() else None

    async def accept(self, info: dict[str, typing.Any] | None = None) -> None:
        await self._send(protocol.encode_model(Op.ACCEPT, Accept(info=info or {})))

    async def reject(self, reason: str) -> None:
        await self._send(protocol.encode_model(Op.REJECT, Reject(reason=reason)))
        self._mark_closed(reason)

    async def wait_accepted(self) -> Accept:
        """Wait for the executor's ACCEPT; raises :class:`StreamRejected` on REJECT."""
        return await asyncio.shield(self._accepted)

    async def ping(self, timeout: float | None = None) -> None:
        self._pong.clear()
        await self._send(protocol.encode(Op.PING))
        await asyncio.wait_for(self._pong.wait(), timeout)

    # -- data ----------------------------------------------------------------

    async def read(self) -> bytes:
        """Next chunk of the peer's data, ``b""`` once it sent EOF."""
        if self._received_eof and self._inbound.empty():
            return b""
        item = await self._inbound.get()
        if item is _EOF:
            self._received_eof = True
            return b""
        if item is _CLOSED:
            # keep answering the same to every later read
            self._inbound.put_nowait(_CLOSED)
            raise StreamClosed(self.close_reason or "")
        self._transport.consumed(len(item))
        return item

    async def write(self, data: bytes) -> None:
        self._check_writable()
        for start in range(0, len(data), protocol.MAX_DATA):
            chunk = data[start : start + protocol.MAX_DATA]
            await self._send(protocol.encode_data(self._send_seq, chunk))
            self._send_seq += 1

    async def write_eof(self) -> None:
        """Tell the peer no more data follows; reading from it stays possible."""
        self._check_writable()
        self._sent_eof = True
        await self._send(protocol.encode_eof(self._send_seq))
        self._send_seq += 1

    async def close(self, reason: str = "") -> None:
        """End the stream deliberately, telling the peer why."""
        if self.closed.is_set():
            return
        self._mark_closed(reason)
        try:
            await self._transport.send(protocol.encode_model(Op.CLOSE, Close(reason=reason)))
        except Exception:
            # the transport may be the very thing that went away
            pass

    # -- inbound -------------------------------------------------------------

    async def feed(self, message: bytes) -> None:
        """Hand one message from the peer to this stream. Blocks when the reader is behind."""
        op, payload = protocol.decode(message)
        match op:
            case Op.DATA:
                seq, data = protocol.decode_sequenced(payload)
                if await self._accept_seq(seq):
                    await self._inbound.put(data)
            case Op.EOF:
                seq, _ = protocol.decode_sequenced(payload)
                if await self._accept_seq(seq):
                    await self._inbound.put(_EOF)
            case Op.HELLO:
                hello = Hello.model_validate_json(payload)
                if self._peer_hello.done():
                    if hello.attempt > self._peer_hello.result().attempt:
                        self._peer_hello = asyncio.get_running_loop().create_future()
                        self._peer_hello.set_result(hello)
                        self.peer_reconnected.set()
                else:
                    self._peer_hello.set_result(hello)
            case Op.ACCEPT:
                if not self._accepted.done():
                    self._accepted.set_result(Accept.model_validate_json(payload))
            case Op.REJECT:
                reason = Reject.model_validate_json(payload).reason
                self._mark_closed(reason, rejected=True)
            case Op.CLOSE:
                self._mark_closed(Close.model_validate_json(payload).reason)
            case Op.PING:
                await self._send(protocol.encode(Op.PONG))
            case Op.PONG:
                self._pong.set()
            case _:
                await self.close(f"unexpected op {op.name} between ends")

    async def _accept_seq(self, seq: int) -> bool:
        """
        Keep the stream exactly-once: drop the duplicate a reconnect may cause and,
        since a frame lost on the way cannot be recovered, end the stream on a gap.
        """
        if seq < self._recv_seq:
            return False
        if seq > self._recv_seq:
            await self.close(f"sequence gap: expected {self._recv_seq}, got {seq}")
            return False
        self._recv_seq += 1
        return True

    # -- internals -----------------------------------------------------------

    def _check_writable(self) -> None:
        if self.closed.is_set():
            raise StreamClosed(self.close_reason or "")
        if self._sent_eof:
            raise RuntimeError("cannot write after EOF")

    async def _send(self, message: bytes) -> None:
        if self.closed.is_set():
            raise StreamClosed(self.close_reason or "")
        await self._transport.send(message)

    def _mark_closed(self, reason: str, rejected: bool = False) -> None:
        if self.closed.is_set():
            return
        self.close_reason = reason
        self.closed.set()
        error = StreamRejected(reason) if rejected else StreamClosed(reason)
        if not self._accepted.done():
            self._accepted.set_exception(error)
            self._accepted.exception()  # retrieved: nobody waiting is not an error
        if not self._peer_hello.done():
            self._peer_hello.set_exception(error)
            self._peer_hello.exception()
        # wake readers; drops nothing already queued ahead of the sentinel
        try:
            self._inbound.put_nowait(_CLOSED)
        except asyncio.QueueFull:
            # a reader will get here once it drains the queue
            asyncio.get_running_loop().create_task(self._inbound.put(_CLOSED))
