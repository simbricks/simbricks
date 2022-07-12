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
from time import gmtime, strftime

from results.utils.netperf import parse_netperf_run


def fmt_lat(lat):
    if not lat:
        return ''

    x = float(lat)
    if x >= 1000.:
        return f'{x / 1000:.1f}\\,ms'
    else:
        return f'{int(x)}\\,$\\mu$s'


# pylint: disable=redefined-outer-name
def fmt_tp(tp):
    if not tp:
        return ''

    x = float(tp)
    if x > 1000.:
        return f'{x / 1000:.2f}\\,G'
    else:
        return f'{int(x)}\\,M'


hosts = [('qemu', 'QK'), ('qt', 'QT'), ('gem5', 'G5')]
nics = [('i40e', 'IB'), ('cd_bm', 'CB'), ('cd_verilator', 'CV')]
nets = [('switch', 'SW'), ('ns3', 'NS')]

outdir = sys.argv[1]

for (h, h_l) in hosts:
    for (nic, nic_l) in nics:
        for (net, net_l) in nets:
            path = f'{outdir}/netperf-{h}-{net}-{nic}-1.json'
            data = parse_netperf_run(path)
            if 'simtime' in data:
                t = strftime('%H:%M:%S', gmtime(data['simtime']))
            else:
                t = ''

            tp = fmt_tp(data.get('throughput', ''))
            latMean = fmt_lat(data.get('latenyMean', ''))
            latTail = fmt_lat(data.get('latenyTail', ''))
            print(f'  {h_l} & {nic_l} & {net_l} & {tp} & {latMean} & t \\\\')
