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

import enum

from simbricks.orchestration.system import base as system_base
from simbricks.orchestration.utils import base as utils_base


class Time(enum.IntEnum):
    Picoseconds = 10 ** (-3)
    Nanoseconds = 1
    Microseconds = 10 ** (3)
    Milliseconds = 10 ** (6)
    Seconds = 10 ** (9)


class Channel:

    def __init__(self, chan: system_base.Channel):
        self._synchronized: bool = False
        self.sync_period: int = 500  # nano seconds
        self.sys_channel: system_base.Channel = chan

    def full_name(self) -> str:
        return "channel." + self.name

    def set_sync_period(self, amount: int, ratio: Time = Time.Nanoseconds) -> None:
        utils_base.has_expected_type(obj=ratio, expected_type=Time)
        self.sync_period = amount * ratio
