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
Transferring artifacts between a main runner and its executors.

An artifact travels as a sequence of frames rather than in one piece, so neither
side ever holds more than a single chunk of it in memory. Both directions use
the same protocol: input artifacts are pushed down to the executor, output
artifacts sent back up.
"""

from __future__ import annotations

import enum
import hashlib
import itertools
import os
import pathlib
import tempfile
import typing

import pydantic

from simbricks.runner import framing
from simbricks.utils import artifatcs as utils_art
from simbricks.utils.artifatcs import Artifact, ArtifactInfo, ArtifactKind

__all__ = ["Artifact", "ArtifactInfo", "ArtifactKind"]

#: How much of an artifact a single frame carries.
CHUNK_SIZE = 1 << 20


class Operation(str, enum.Enum):
    """What an artifact frame does to the transfer it belongs to."""

    BEGIN = "begin"
    DATA = "data"
    END = "end"
    ABORT = "abort"


class _FrameMetadata(pydantic.BaseModel):
    """What every artifact frame says about itself, ahead of its payload."""

    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")

    #: Which transfer on this channel the frame belongs to.
    sid: int


class BeginMetadata(_FrameMetadata):
    """Announces a transfer, along with the artifact's identity and size."""

    op: typing.Literal[Operation.BEGIN] = Operation.BEGIN
    info: ArtifactInfo
    size: int


class DataMetadata(_FrameMetadata):
    """Carries the next chunk of the artifact as the frame's payload."""

    op: typing.Literal[Operation.DATA] = Operation.DATA


class EndMetadata(_FrameMetadata):
    """Completes a transfer, along with the size and checksum to verify against."""

    op: typing.Literal[Operation.END] = Operation.END
    size: int
    sha256: str


class AbortMetadata(_FrameMetadata):
    """Gives up on a transfer, along with the reason."""

    op: typing.Literal[Operation.ABORT] = Operation.ABORT
    reason: str


#: The metadata of any artifact frame, told apart by its ``op``.
FrameMetadata = typing.Annotated[
    BeginMetadata | DataMetadata | EndMetadata | AbortMetadata,
    pydantic.Field(discriminator="op"),
]

_METADATA_ADAPTER: pydantic.TypeAdapter[FrameMetadata] = pydantic.TypeAdapter(FrameMetadata)


def _encode(metadata: FrameMetadata, payload: bytes = b"") -> framing.ArtifactFrame:
    return framing.ArtifactFrame.pack(metadata.model_dump_json().encode("utf-8"), payload)


def _decode(frame: framing.ArtifactFrame) -> tuple[FrameMetadata, bytes]:
    metadata, payload = frame.unpack()
    return _METADATA_ADAPTER.validate_json(metadata), payload


def _spool(spool_dir: pathlib.Path) -> tuple[int, pathlib.Path]:
    spool_dir.mkdir(parents=True, exist_ok=True)
    handle, spooled = tempfile.mkstemp(dir=spool_dir, prefix=".artifact-", suffix=".partial")
    return handle, pathlib.Path(spooled)


def spool_file(spool_dir: pathlib.Path) -> pathlib.Path:
    """Create an empty file in ``spool_dir``, which the caller owns and removes."""
    handle, path = _spool(spool_dir)
    os.close(handle)
    return path


class RelayArtifactSink(utils_art.ArtifactSink):
    """Hands artifacts to whoever is on the other end of a channel."""

    def __init__(self, channel: framing.FrameChannel, chunk_size: int = CHUNK_SIZE) -> None:
        self._channel = channel
        self._chunk_size = chunk_size
        # Stream ids only tell apart the transfers in flight on this channel in
        # this direction, so a counter per sink is enough.
        self._stream_ids = itertools.count(1)

    async def store(self, artifact: Artifact) -> None:
        # Chunks are handed to the channel one at a time, so a peer that stops
        # reading stalls this loop rather than letting the artifact pile up.
        stream_id = next(self._stream_ids)
        digest = hashlib.sha256()
        await self._channel.send(
            _encode(
                BeginMetadata(sid=stream_id, info=artifact.info, size=artifact.path.stat().st_size)
            )
        )
        try:
            sent = 0
            with artifact.path.open("rb") as file:
                while chunk := file.read(self._chunk_size):
                    digest.update(chunk)
                    sent += len(chunk)
                    await self._channel.send(_encode(DataMetadata(sid=stream_id), chunk))
        except Exception as error:
            await self._channel.send(_encode(AbortMetadata(sid=stream_id, reason=str(error))))
            raise

        await self._channel.send(
            _encode(EndMetadata(sid=stream_id, size=sent, sha256=digest.hexdigest()))
        )


class _IncomingArtifact:
    """An artifact still arriving, and the spool file it is being written to."""

    def __init__(self, spool_dir: pathlib.Path, info: ArtifactInfo) -> None:
        handle, path = _spool(spool_dir)
        self.artifact = Artifact(path=path, info=info)
        self._file = open(handle, "wb")
        self._digest = hashlib.sha256()
        self._received = 0

    def write(self, payload: bytes) -> None:
        self._digest.update(payload)
        self._received += len(payload)
        self._file.write(payload)

    def complete(self, size: int, sha256: str) -> Artifact:
        """Finish the spool file, refusing what lost or corrupted bytes on the way."""
        self._file.close()
        checksum = self._digest.hexdigest()
        if self._received != size or checksum != sha256:
            self.discard()
            raise RuntimeError(
                f"artifact {self.artifact.info.name} arrived incomplete:"
                f" expected {size} bytes with checksum {sha256},"
                f" received {self._received} bytes with checksum {checksum}"
            )
        return self.artifact

    def discard(self) -> None:
        self._file.close()
        self.artifact.path.unlink(missing_ok=True)


class ArtifactReceiver:
    """
    Collects artifact frames into spool files.

    Several artifacts can be in flight at once, told apart by stream id.
    """

    def __init__(self, spool_dir: pathlib.Path) -> None:
        self._spool_dir = spool_dir
        self._incoming: dict[int, _IncomingArtifact] = {}

    def handle_frame(self, frame: framing.ArtifactFrame) -> Artifact | None:
        """Take one artifact frame, returning the artifact once it is complete."""
        metadata, payload = _decode(frame)

        match metadata:
            case BeginMetadata():
                self._begin(metadata)
                return None
            case DataMetadata():
                self._get(metadata.sid).write(payload)
                return None
            case EndMetadata():
                return self._pop(metadata.sid).complete(metadata.size, metadata.sha256)
            case AbortMetadata():
                self._pop(metadata.sid).discard()
                raise RuntimeError(f"sender aborted artifact transfer: {metadata.reason}")

    def _get(self, stream_id: int) -> _IncomingArtifact:
        if stream_id not in self._incoming:
            raise RuntimeError(f"no artifact transfer with id {stream_id}")
        return self._incoming[stream_id]

    def _pop(self, stream_id: int) -> _IncomingArtifact:
        incoming = self._get(stream_id)
        del self._incoming[stream_id]
        return incoming

    def _begin(self, metadata: BeginMetadata) -> None:
        if metadata.sid in self._incoming:
            raise RuntimeError(f"artifact transfer with id {metadata.sid} already in progress")
        self._incoming[metadata.sid] = _IncomingArtifact(self._spool_dir, metadata.info)

    def close(self) -> None:
        """Drop every transfer still in flight, removing its spool file."""
        for incoming in self._incoming.values():
            incoming.discard()
        self._incoming.clear()
