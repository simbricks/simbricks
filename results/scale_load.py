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
import math
import os
import sys

num_runs = 3
if len(sys.argv) != 2:
    print('Usage: python3 ScaleLoad.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'

# FIXME: dropped 120 because it looks off
types_of_bw = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

for bw in types_of_bw:
    total_time = 0
    avg_time = 0
    std = 0
    all_time = []
    for i in range(1, num_runs + 1):
        log_path = f'{basedir}gt-ib-sw-Load-{bw}m-{i}.json'

        diff_time = ''
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as log:
                exp_log = json.load(log)
                start_time = exp_log['start_time']
                end_time = exp_log['end_time']
                diff_time = (end_time - start_time) / 60  #min
                total_time += diff_time
                all_time.append(diff_time)
                diff_time = str(diff_time)

        #print('%d\t%s' % (bw, diff_time))

    avg_time = total_time / num_runs
    #print('avg_time: ' + str(avg_time))

    for i in range(0, num_runs):
        std += (all_time[i] - avg_time) * (all_time[i] - avg_time)

    std = std / num_runs
    std = math.sqrt(std)
    #print(str(std))
    print(f'{bw} {avg_time} {std}')
