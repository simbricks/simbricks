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

import itertools
import sys

from results.utils.iperf import parse_iperf

if len(sys.argv) != 2:
    print('Usage: dctcp.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'

types_of_host = ['tb', 'gt', 'qt']
mtus = [1500, 4000]
max_k = 199680
k_step = 16640

configs = list(itertools.product(types_of_host, mtus))
confignames = [h + '-' + str(mtu) for h, mtu in configs]
print('\t'.join(['threshold'] + confignames))

for k_val in range(0, max_k + 1, k_step):
    line = [str(k_val)]
    for h, mtu in configs:
        path_pat = f'{basedir}{h}-ib-dumbbell-DCTCPm{k_val}-{mtu}'
        res = parse_iperf(path_pat)

        if res['avg'] is None:
            line.append('')
            continue

        tp = res['avg']
        # TP * (MTU ) / (MTU - IP (20) - TCP w/option (24))
        if h in ('gt', 'qt'):
            tp_calib = tp * (mtu) / (mtu - 20 - 24)
        else:
            # TP * (MTU + ETH(14) + PHY(24)) / (MTU - IP (20)
            # - TCP w/option (24))
            tp_calib = tp * (mtu + 14 + 24) / (mtu - 20 - 24)
        line.append(f'{tp_calib:.2f}')

    print('\t'.join(line))
