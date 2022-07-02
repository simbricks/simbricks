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

import os
import sys

if len(sys.argv) != 2:
    print('Usage: ns3-dctcp.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'

max_k = 199680
k_step = 16640
mtu = 4000

confignames = ['ns3-4000']
print('\t'.join(['threshold'] + confignames))

for k_val in range(0, max_k + 1, k_step):
    line = [str(k_val)]
    path_pat = f'{basedir}dctcp-modes-tput-4000-{k_val}-50us.dat'

    tps = []

    if not os.path.isfile(path_pat):
        print('no result file at: ' + path_pat)
        sys.exit()
    with open(path_pat, 'r', encoding='utf-8') as f:
        lines = f.readlines()

        tp = float(lines[1].split()[2]) / 1000
        tps.append(tp)

        tp = float(lines[2].split()[2]) / 1000
        tps.append(tp)

    total_tp = sum(tps)

    # TP * (MTU + PPP(2)) / (MTU - IP (20) - TCP w/option (24))
    tp_calib = total_tp * (mtu + 2) / (mtu - 20 - 24)
    line.append(f'{tp_calib:.2f}')
    print('\t'.join(line))
