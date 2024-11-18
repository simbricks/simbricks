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

import json

from simbricks.orchestration.utils import base as util_base
from simbricks.orchestration.system import base as sys_base


def toJSON(system: sys_base.System) -> dict:

    json_obj = {}

    util_base.has_attribute(system, "toJSON")
    json_obj["system"] = system.toJSON()

    channels: set[sys_base.Channel] = set()
    for comp in system.all_component:
        for inf in comp.interfaces():
            channels.add(inf.channel)

    channels_json = []
    for chan in channels:
        util_base.has_attribute(chan, "toJSON")
        channels_json.append(chan.toJSON())
    json_obj["channels"] = channels_json

    return json.dumps({"specification": json_obj})
