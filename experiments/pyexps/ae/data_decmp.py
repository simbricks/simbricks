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

import glob
import itertools
import json
import os
import sys

if len(sys.argv) != 2:
    print('Usage: data_decmp.py OUTFILE')
    sys.exit(1)

out_file = sys.argv[1]

if not os.path.isfile(out_file):
    print('no result file at: ' + out_file)
    exit(0)

f = open(out_file, 'r')
lines = f.readlines()

for line in lines:
    if 'start:' in line:
        start_time = float(line.split()[1])

    if 'end:' in line:
        end_time = float(line.split()[1])

time_diff = end_time - start_time
print('SimTime: %d (s)' % (time_diff))

f.close()
