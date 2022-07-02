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
import sys

# How to use
# $ python3 modetcp.py paper_data/modetcp
#

mode = ['0', '1']
nics = ['cb', 'cv', 'ib']
num_client = ['1', '4']

outdir = sys.argv[1]


# pylint: disable=redefined-outer-name
def parse_sim_time(path):
    ret = {}
    if not os.path.exists(path):
        return ret
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ret['simtime'] = (data['end_time'] - data['start_time']) / 60
    f.close()
    return ret


for c in num_client:
    print(f'{c}-client ModES  Epoch')
    for n in nics:
        line = f'{n}'
        for m in mode:
            path = f'{outdir}/mode-{m}-gt-{n}-switch-{c}-1.json'
            data = parse_sim_time(path)
            t = data.get('simtime', '')
            line = f'{line} {t}'
        print(line)
