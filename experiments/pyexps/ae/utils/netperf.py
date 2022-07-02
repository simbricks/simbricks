# Copyright 2021 Max Planck Institute for Software Systems, and
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
import os
import re


def parse_netperf_run(path):
    ret = {}

    if not os.path.exists(path):
        return ret
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ret['simtime'] = data['end_time'] - data['start_time']

    tph_pat = re.compile(r'Size\s*Size\s*Size\s*Time\s*Throughput.*')
    start = None
    i = 0
    lines = data['sims']['host.client.0']['stdout']
    for l in lines:
        if tph_pat.match(l):
            start = i
            break
        i += 1

    if start is not None:
        tp_line = lines[start + 3]
        tp_pat = re.compile(r'\s*\d*\s*\d*\s*\d*\s*[0-9\.]*\s*([0-9\.]*).*')
        m = tp_pat.match(tp_line)
        ret['throughput'] = float(m.group(1))

    lath_pat = re.compile(r'\s*Mean Latency.*')
    start = None
    i = 0
    lines = data['sims']['host.client.0']['stdout']
    for l in lines:
        if lath_pat.match(l):
            start = i
            break
        i += 1

    if start is not None:
        lat_line = lines[start + 1]
        lat_pat = re.compile(
            r'\s*([-0-9\.]*),([-0-9\.]*),([-0-9\.]*),([-0-9\.]*).*'
        )
        m = lat_pat.match(lat_line)
        ret['latenyMean'] = float(m.group(1))
        ret['latenyTail'] = float(m.group(4))

    return ret
