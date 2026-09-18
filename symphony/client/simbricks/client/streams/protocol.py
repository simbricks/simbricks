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
The message format spoken end to end over a run stream.

The backend relays websocket frames verbatim, so everything the two ends need
to agree on lives in the frames themselves: one op byte, then a payload whose
shape the op determines. Control ops carry JSON; DATA and EOF carry a sequence
number so that the one frame the relay may deliver twice after a reconnect is
dropped rather than applied twice.
"""

from __future__ import annotations

import enum
import struct
import typing

import pydantic

#: Largest DATA payload (without the sequence header) an end may send in one
#: message. Keeps a single message well below relay and websocket frame limits
#: and lets the runner⇄executor leg account credit at a useful granularity.
MAX_DATA = 64 * 1024


class Op(enum.IntEnum):
    """The byte a message's kind travels as."""

    #: First message from each side after attaching; the relay holds it until the
    #: peer is there, so receiving it means the peer is present.
    HELLO = 0
    #: The executor's answers to the stream's target.
    ACCEPT = 1
    REJECT = 2
    #: Sequenced bytes, and a sequenced half-close.
    DATA = 3
    EOF = 4
    #: Deliberate end of the stream, as opposed to a socket going away.
    CLOSE = 5
    #: Liveness of the far end, which the relay does not report.
    PING = 6
    PONG = 7

    # Only on the runner⇄executor leg, never between the ends.
    OPEN = 16
    CREDIT = 17


class Hello(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    side: typing.Literal["client", "executor"]
    #: Counts this side's attachments to the stream; a higher number than
    #: before tells the peer that this side reconnected.
    attempt: int = 1


class Accept(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    #: Whatever the target resolved to, e.g. a path or port. Opaque.
    info: dict[str, typing.Any] = pydantic.Field(default_factory=dict)


class Reject(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    reason: str


class Close(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    reason: str = ""


class Open(pydantic.BaseModel):
    """Runner⇄executor only: opens a stream on the frame channel."""

    model_config = pydantic.ConfigDict(extra="forbid")

    target: str
    run_id: str
    run_fragment_id: str
    params: dict[str, typing.Any] = pydantic.Field(default_factory=dict)
    #: Bytes the sender of this message will accept before granting credit.
    window: int


_SEQ = struct.Struct("!I")
_CREDIT = struct.Struct("!I")


def encode(op: Op, payload: bytes = b"") -> bytes:
    return bytes((op,)) + payload


def decode(message: bytes) -> tuple[Op, bytes]:
    if not message:
        raise ValueError("empty stream message")
    return Op(message[0]), message[1:]


def encode_model(op: Op, model: pydantic.BaseModel) -> bytes:
    return encode(op, model.model_dump_json().encode("utf-8"))


def encode_data(seq: int, data: bytes) -> bytes:
    return encode(Op.DATA, _SEQ.pack(seq) + data)


def encode_eof(seq: int) -> bytes:
    return encode(Op.EOF, _SEQ.pack(seq))


def decode_sequenced(payload: bytes) -> tuple[int, bytes]:
    """Split the sequence number off a DATA or EOF payload."""
    (seq,) = _SEQ.unpack_from(payload)
    return seq, payload[_SEQ.size :]


def encode_credit(amount: int) -> bytes:
    return encode(Op.CREDIT, _CREDIT.pack(amount))


def decode_credit(payload: bytes) -> int:
    (amount,) = _CREDIT.unpack(payload)
    return amount
