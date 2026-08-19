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
Frames carried over the connection between a main runner and an executor.

The connection multiplexes bundles of events and the raw bytes of artifacts.
Both travel as length-prefixed frames, so a large artifact is split into many
frames instead of one enormous message and events keep flowing meanwhile.
"""

from __future__ import annotations

import abc
import asyncio
import enum
import json
import struct
import typing
from collections.abc import Awaitable, Callable

from simbricks.client.namespace import EventFromRunner_U, EventToRunner_U

_HEADER = struct.Struct("!BQ")
_HEADER_LENGTH = _HEADER.size


class FrameType(enum.IntEnum):
    """The byte a frame's kind travels as."""

    EVENTS = 1
    ARTIFACT = 2


async def _read_exactly(read: Callable[[int], Awaitable[bytes]], length: int) -> bytes:
    assert length >= 0
    data = bytes()
    while len(data) < length:
        chunk = await read(length - len(data))
        if len(chunk) == 0:
            raise RuntimeError("connection broken")
        data += chunk
    return data


class Frame(abc.ABC):
    """One frame on the connection, of a kind its subclass names."""

    TYPE: typing.ClassVar[FrameType]

    def __init__(self, body: bytes) -> None:
        self.body = body

    def encode(self) -> bytes:
        return _HEADER.pack(self.TYPE, len(self.body)) + self.body

    @staticmethod
    async def read(read: Callable[[int], Awaitable[bytes]]) -> Frame:
        # Takes the connection rather than a block of bytes: the body's length
        # only becomes known once the header has been read.
        frame_type, length = _HEADER.unpack(await _read_exactly(read, _HEADER_LENGTH))
        body = await _read_exactly(read, length)
        if frame_type not in _FRAME_TYPES:
            raise RuntimeError(f"received frame of unknown type {frame_type}")
        return _FRAME_TYPES[frame_type](body)


def _event_to_dict(event: EventToRunner_U | EventFromRunner_U) -> dict:
    assert hasattr(event, "to_dict")
    return {"type": event.__class__.__name__, "data": event.to_dict()}


def _event_from_dict(event_dict: dict) -> EventToRunner_U | EventFromRunner_U:
    assert "type" in event_dict
    assert "data" in event_dict

    ty = event_dict["type"]
    data = event_dict["data"]

    types_to_check = typing.get_args(EventFromRunner_U)
    types_to_check += typing.get_args(EventToRunner_U)
    for model_type in types_to_check:
        if model_type.__name__ == ty:
            assert hasattr(model_type, "from_dict")
            event = model_type.from_dict(data)
            return event

    raise Exception(f"Cannot resolve event dict: {event_dict}")


class EventFrame(Frame):
    """A bundle of events, as a UTF-8 JSON array."""

    TYPE = FrameType.EVENTS

    @classmethod
    def pack(cls, events: list[EventToRunner_U] | list[EventFromRunner_U]) -> EventFrame:
        return cls(json.dumps([_event_to_dict(event) for event in events]).encode("utf-8"))

    def unpack(self) -> list[EventToRunner_U | EventFromRunner_U]:
        return [_event_from_dict(event) for event in json.loads(self.body.decode("utf-8"))]


class ArtifactFrame(Frame):
    """
    Part of an artifact transfer, see :mod:`simbricks.runner.artifacts`.

    The body is a length-prefixed block of metadata followed by the payload that
    metadata describes.
    """

    TYPE = FrameType.ARTIFACT

    _METADATA = struct.Struct("!I")

    @classmethod
    def pack(cls, metadata: bytes, payload: bytes = b"") -> ArtifactFrame:
        return cls(cls._METADATA.pack(len(metadata)) + metadata + payload)

    def unpack(self) -> tuple[bytes, bytes]:
        (length,) = self._METADATA.unpack_from(self.body)
        start = self._METADATA.size
        return self.body[start : start + length], self.body[start + length :]


_FRAME_TYPES: dict[int, type[Frame]] = {frame.TYPE: frame for frame in (EventFrame, ArtifactFrame)}


class FrameChannel:
    """
    A connection, seen as whole frames rather than bytes.

    Sending is serialized so frames from different senders interleave but never
    overlap; receiving is serialized because reading a frame spans several
    reads. The two locks must stay separate: one lock would stop a peer that is
    sending a large artifact from reading, so two peers transferring at once
    would fill each other's buffers with neither able to drain.
    """

    def __init__(
        self,
        read: Callable[[int], Awaitable[bytes]],
        write: Callable[[bytes], Awaitable[None]],
    ) -> None:
        self._read = read
        self._write = write
        self._send_lock = asyncio.Lock()
        self._receive_lock = asyncio.Lock()

    async def send(self, frame: Frame) -> None:
        data = frame.encode()
        async with self._send_lock:
            await self._write(data)

    async def receive(self) -> Frame:
        async with self._receive_lock:
            return await Frame.read(self._read)
