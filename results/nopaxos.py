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

from results.utils.parse_nopaxos import parse_nopaxos_run

if len(sys.argv) != 2:
    print('Usage: nopaxos.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'

types_of_seq = ['ehseq', 'swseq']
num_clients = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]

print(
    'num_client ehseq-tput(req/sec) ehseq-lat(us) swseq-tput(req/sec)'
    ' swseq-lat(us)\n'
)

for num_c in num_clients:
    line = [str(num_c)]
    for seq in types_of_seq:

        path_pat = f'{basedir}nopaxos-gt-ib-{seq}-{num_c}-1.json'
        res = parse_nopaxos_run(num_c, path_pat)
        #print(path_pat)

        if ((res['throughput'] is None) or (res['latency'] is None)):
            line.append('')
            line.append('')
            continue

        #print tput and avg. latency
        tput = res['throughput']
        lat = res['latency']

        line.append(f'{tput:.2f}')
        line.append(f'{lat}')

    print(' '.join(line))
