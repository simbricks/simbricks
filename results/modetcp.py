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

import sys
import os
import pathlib
import shutil
import json

# How to use
# $ python3 modetcp.py paper_data/modetcp 
#


mode = ['0', '1']
nics = ['cb', 'cv', 'ib']
num_client = ['1', '4']

outdir = sys.argv[1]

def parse_sim_time(path):
    ret = {}
    if not os.path.exists(path):
        return ret
    with open(path, 'r') as f:
        data = json.load(f)

    ret['simtime'] = (data['end_time'] - data['start_time'])/60
    f.close()
    return ret


for c in num_client:
    print('%s-client ModES  Epoch' % (c))
    for n in nics:
        line = f'{n}'
        for m in mode:
            path = '%s/mode-%s-gt-%s-switch-%s-1.json' % (outdir, m, n, c)
            data = parse_sim_time(path)
            if 'simtime' in data:
                t = data['simtime']
            else:
                t = ''
            line = line + ' ' + f'{t}'
        print(line)
    

