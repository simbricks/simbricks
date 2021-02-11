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

if len(sys.argv) != 2:
    print('Usage: udp.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'

# FIXME: dropped 120 because it looks off
types_of_bw = [0, 20, 40, 60, 80, 100, 140, 200, 500, 800, 1000]


for bw in types_of_bw:
    log_path = '%sgt-ib-wire-UDPs-%dm-1.json' % (basedir, bw)
    if os.path.exists(log_path):
        log = open(log_path, 'r')
        exp_log = json.load(log)
        start_time = exp_log["start_time"]
        end_time = exp_log["end_time"]
        diff_time = (end_time - start_time)/60 #min
        diff_time = str(diff_time)
    else:
        diff_time = ''

    print('%d\t%s' % (bw, diff_time))

    log.close()

