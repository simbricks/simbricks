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
from __future__ import annotations

import asyncio
import logging
import pathlib
import sys

from simbricks.runner.fragment_runner.local import settings
from simbricks.runner.fragment_runner import base as runner_base


class LocalRunner(runner_base.FragmentRunner):

    def __init__(
        self,
        base_url: str,
        workdir: pathlib.Path,
        namespace: str,
        ident: int,
        polling_delay_sec: int,
        runner_ip: str,
        runner_port: int,
        verbose: bool,
    ):
        super().__init__(base_url, workdir, namespace, ident, polling_delay_sec, runner_ip, verbose)
        self.reader: asyncio.StreamReader
        self.writer: asyncio.StreamWriter
        self._runner_port: int = runner_port

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self._runner_ip, self._runner_port)

    async def read(self, length: int) -> bytes:
        return await self.reader.read(length)

    async def write(self, data: bytes) -> None:
        self.writer.write(data)
        await self.writer.drain()


async def amain():
    runner = LocalRunner(
        base_url=settings.runner_settings().base_url,
        workdir=pathlib.Path("./runner-work").resolve(),
        namespace=settings.runner_settings().namespace,
        ident=settings.runner_settings().runner_id,
        polling_delay_sec=settings.runner_settings().polling_delay_sec,
        runner_ip=sys.argv[1],
        runner_port=int(sys.argv[2]),
        verbose=settings.runner_settings().verbose,
    )

    await runner.run()


def setup_logger() -> logging.Logger:
    level = settings.RunnerSettings().log_level
    logging.basicConfig(
        level=level,
        format="%(asctime)s - fragment executor - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    return logger


LOGGER = setup_logger()
runner_base.LOGGER = LOGGER


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
