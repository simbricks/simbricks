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
import sys
from os.path import exists

if len(sys.argv) != 2:
    print('Usage: udp_scale.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'
types_of_client = [1, 4, 9, 14, 20]
bw = 1000

for cl in types_of_client:
    log_path = f'{basedir}gt-ib-sw-Host-{bw}m-{cl}-1.json'

    diff_time = ''
    if exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as log:
            exp_log = json.load(log)
            start_time = exp_log['start_time']
            end_time = exp_log['end_time']
            diff_time = (end_time - start_time) / 60  #min
            diff_time = str(diff_time)

    print(f'{cl}\t{diff_time}')
