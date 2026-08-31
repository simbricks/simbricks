# Copyright 2024 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""A store of built images, shared by every run on a runner.

Entries are named by content hash, so a hit means an image built from the same
base, builder and layers. Files are moved into place under a lock and only ever
whole, so a crashed or half-copied build cannot be mistaken for a finished one.
"""

from __future__ import annotations

import asyncio
import contextlib
import fcntl
import os
import pathlib
import shutil
import typing as tp

_USED = ".used"


class ImageCache:
    """Images kept across runs, under a directory the runner owns."""

    def __init__(self, root: str) -> None:
        self._root = pathlib.Path(root)

    def _entry(self, digest: str) -> pathlib.Path:
        return self._root / digest

    def used(self, digest: str) -> None:
        """Record that a run wanted this entry, for eviction to go by.

        A file we touch ourselves rather than the atime of the image: plenty of
        servers mount with noatime or relatime, where atime would quietly mean
        "when it was written" and eviction would throw away what is used most.
        """
        entry = self._entry(digest)
        if not entry.is_dir():
            return
        marker = entry / _USED
        marker.touch()
        os.utime(marker, None)

    def _last_used(self, entry: pathlib.Path) -> float:
        marker = entry / _USED
        try:
            return marker.stat().st_mtime
        except OSError:
            return entry.stat().st_mtime

    def _entry_size(self, entry: pathlib.Path) -> int:
        total = 0
        for path in entry.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def evict(self, limit: int) -> list[str]:
        """Delete least recently used entries until the cache fits in @limit bytes.

        Returns what it deleted. Skips whatever another run holds, and skips
        everything if a sweep is already in progress: this runs after a store,
        so the next one will finish what this one leaves.
        """
        if not self._root.is_dir():
            return []
        sweep = open(self._root / ".sweep.lock", "w")
        try:
            try:
                fcntl.flock(sweep.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                return []

            entries = [e for e in self._root.iterdir() if e.is_dir()]
            sized = [(self._last_used(e), self._entry_size(e), e) for e in entries]
            total = sum(size for _, size, _ in sized)
            evicted = []
            for _, size, entry in sorted(sized):
                if total <= limit:
                    break
                # A run building into this entry, or linking a file out of it,
                # holds this. Leave it: there will be another sweep.
                held = open(self._root / f"{entry.name}.lock", "w")
                try:
                    try:
                        fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError:
                        continue
                    shutil.rmtree(entry, ignore_errors=True)
                finally:
                    held.close()
                # The lock file itself stays: unlinking one another process is
                # waiting on would leave the two of them holding different
                # inodes, each convinced it has the entry.
                total -= size
                evicted.append(entry.name)
            return evicted
        finally:
            sweep.close()

    def image(self, digest: str, format: str) -> str | None:
        path = self._entry(digest) / f"image.{format}"
        return path.as_posix() if path.is_file() else None

    def boot_artifact(self, digest: str, name: str) -> str | None:
        path = self._entry(digest) / "boot" / name
        return path.as_posix() if path.is_file() else None

    @contextlib.asynccontextmanager
    async def locked(self, digest: str) -> tp.AsyncIterator[None]:
        """Hold the entry against other runs while building or storing it.

        Between processes, where the in-process lock says nothing. Taken in a
        thread: flock blocks, and the event loop has simulators to run.
        """
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._root / f"{digest}.lock"
        handle = open(path, "w")
        try:
            await asyncio.to_thread(fcntl.flock, handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            handle.close()

    def _place(self, source: str, target: pathlib.Path) -> None:
        """Put a copy of @source at @target, atomically and cheaply if possible."""
        target.parent.mkdir(parents=True, exist_ok=True)
        # Whatever a run that died mid-copy left behind. Only reachable holding
        # the entry's lock, so nobody else's copy is in flight.
        for leftover in target.parent.glob(f".{target.name}.*"):
            leftover.unlink(missing_ok=True)
        staged = target.with_name(f".{target.name}.{os.getpid()}")
        try:
            # A hard link so an image is stored and taken out without copying
            # gigabytes. Safe because nothing writes to an image in place: a
            # simulator that needs to write gets a copy-on-write overlay.
            os.link(source, staged)
        except OSError:
            # Different filesystems, or a filesystem without hard links.
            shutil.copy2(source, staged)
        os.replace(staged, target)

    def store_image(self, digest: str, format: str, path: str) -> None:
        self._place(path, self._entry(digest) / f"image.{format}")

    def store_boot_artifact(self, digest: str, name: str, path: str) -> None:
        self._place(path, self._entry(digest) / "boot" / name)

    def take_out(self, cached: str, target: str) -> bool:
        """Put a cached file where this run wants it. False if it is gone.

        It can be gone: on a shared filesystem the entry may have been evicted
        by another machine since it was looked up, and an NFS client can be
        told about that only after it has cached the directory. The caller
        treats that as a miss rather than an error.
        """
        try:
            self._place(cached, pathlib.Path(target))
        except OSError:
            return False
        return True
