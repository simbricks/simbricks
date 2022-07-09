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
    print('Usage: data_dist.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1]

types_of_host = [2, 8, 16, 32]


def time_diff_min(data):
    start_time = data['start_time']
    end_time = data['end_time']

    time_diff_in_min = (end_time - start_time) / 60
    return time_diff_in_min


print('# Number of hosts' + '\t' + 'Sim.Time')

for workload in types_of_host:

    line = [str(workload)]
    path_pat = '%srun-%d.out' % (basedir, workload)

    if not os.path.isfile(path_pat):
        #print("no result file at: " + path_pat)
        line.append(' ')
    else:
        with open(path_pat, 'r') as f:
            read_lines = f.readlines()

            for l in read_lines:
                if 'START' in l:
                    start_time = float(l.split()[1])
                    #print("start_time: %d" % start_time)

                if 'EXIT' in l or 'KILLED' in l:
                    end_time = float(l.split()[1])
                    #print("end_time: %d" % end_time)

            sim_time = (end_time - start_time) / 60
            line.append('%d' % sim_time)

    print('\t'.join(line))
