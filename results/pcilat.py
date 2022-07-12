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

from results.utils.iperf import parse_iperf

if len(sys.argv) != 2:
    print('Usage: pcilat.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'

types_of_host = ['gt']
types_of_nic = ['cb', 'ib']
lats = [500, 1000]

configs = [
    ('gt', 'cb', 'Corundum'),
    ('gt', 'ib', 'Intel X710'),
]

print('\t'.join(['config'] + list(map(str, lats))))

for (ht, nt, lab) in configs:
    cols = [str(lab)]
    for lat in lats:
        path_pat = f'{basedir}pcilat-{ht}-{nt}-switch-{lat}'
        res = parse_iperf(path_pat)

        if res['avg'] is None:
            cols.append('')
        else:
            cols.append(str(res['avg']))

    print('\t'.join(cols))
