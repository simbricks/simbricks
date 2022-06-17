# Copyright 2022 Max Planck Institute for Software Systems, and
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
""" Generates data file for dist_memcache scalability graph. First column is
the number of hosts, second column the qemu timing simulation time in hours,
and the third column is the gem5 simulation time."""

import sys
import json

if len(sys.argv) != 2:
    print('Usage: dist_memcache.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'
n_hosts_per_rack = 40
racks = [1, 5, 10, 15, 25]
host_types = ['qt', 'gem5']

for n_racks in racks:
  l = str(n_racks * n_hosts_per_rack)
  for host_type in host_types:
    log_path = '%sdist_memcache-%s-%d-%d-1.json' % (basedir, host_type,
                                                    n_racks, n_hosts_per_rack)
    try:
        log = open(log_path, 'r')
    except:
        diff_time = ''
    else:
        exp_log = json.load(log)
        start_time = exp_log["start_time"]
        end_time = exp_log["end_time"]
        diff_time = float(end_time - start_time)/60/60

    l += '\t' + str(diff_time)

  print(l)


