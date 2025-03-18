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
import datetime
import json
import logging
import pathlib
import traceback
import typing
import uuid

from simbricks import client
from simbricks.client.opus import base as opus_base
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.system import base as sys_base
from simbricks.runner import settings
from simbricks.runner.fragment_runner import base as runner_base
from simbricks.runtime import simulation_executor as sim_exec
from simbricks.schemas import base as schemas
from simbricks.utils import base as utils_base
from simbricks.utils import artifatcs as utils_art

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import proxy as inst_proxy


class LocalRunner(runner_base.FragmentRunner):

    async def read(self, length: int) -> bytes:
        pass

    async def write(self, data: bytes) -> None:
        pass


async def amain():
    runner = LocalRunner(
        base_url=settings.runner_settings().base_url,
        workdir=pathlib.Path("./runner-work").resolve(),
        namespace=settings.runner_settings().namespace,
        ident=settings.runner_settings().runner_id,
        polling_delay_sec=settings.runner_settings().polling_delay_sec,
        runner_ip=settings.runner_settings().runner_ip,
    )

    await runner.run()


def setup_logger() -> logging.Logger:
    level = settings.RunnerSettings().log_level
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger(__name__)
    return logger


LOGGER = setup_logger()


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
