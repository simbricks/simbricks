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

import fnmatch
import glob
import itertools
import json
import os
import re
import sys


def parse_iperf_run(data, skip=1, use=8):
    tp_pat = re.compile(
        r'\[ *\d*\] *([0-9\.]*)- *([0-9\.]*) sec.*Bytes *([0-9\.]*) ([GM])bits.*'
    )
    tps_time = {}
    for hn in fnmatch.filter(data['sims'].keys(), 'host.client.*'):
        sim = data['sims'][hn]
        for l in sim['stdout']:
            m = tp_pat.match(l)
            if not m:
                continue

            time = int(float(m.group(1)))
            if time < skip:
                continue
            if time >= skip + use:
                continue

            if not time in tps_time:
                tps_time[time] = []

            if m.group(4) == 'G':
                tps_time[time].append(float(m.group(3)))
            elif m.group(4) == 'M':
                m_tps = float(m.group(3)) / 1000
                tps_time[time].append(m_tps)

    tps = []
    for t in sorted(tps_time.keys()):
        x = sum(tps_time[t])
        tps.append(x)

    if len(tps) == 0:
        return None
    return sum(tps) / len(tps)


def parse_iperf(basename, skip=1, use=8):
    runs = []
    for path in glob.glob(basename + '-*.json'):
        if path == basename + '-0.json':
            # skip checkpoints
            continue

        with open(path, 'r') as f:
            data = json.load(f)
        result = parse_iperf_run(data, skip, use)
        if result is not None:
            runs.append(result)

    if not runs:
        return {'avg': None, 'min': None, 'max': None}
    else:
        return {
            'avg': sum(runs) / len(runs), 'min': min(runs), 'max': max(runs)
        }
    result = {}
