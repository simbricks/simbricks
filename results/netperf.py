from utils.netperf import *
import sys
import os.path
from time import strftime
from time import gmtime


def fmt_lat(lat):
    if not lat:
        return ''

    x = float(lat)
    if x >= 1000.:
        return '%.1f\\,ms' % (x / 1000)
    else:
        return '%d\\,$\\mu$s' % (int(x))

def fmt_tp(tp):
    if not tp:
        return ''

    x = float(tp)
    if x > 1000.:
        return '%.2f\\,G' % (x / 1000)
    else:
        return '%d\\,M' % (int(x))

hosts = [('qemu','QK'), ('qt','QT'), ('gem5','G5')]
nics = [('i40e','IB'), ('cd_bm','CB'), ('cd_verilator','CV')]
nets = [('switch','SW'), ('ns3','NS')]

outdir = sys.argv[1]

for (h,h_l) in hosts:
 for (nic, nic_l) in nics:
  for (net, net_l) in nets:
    path = '%s/netperf-%s-%s-%s-1.json' % (outdir, h, net, nic)
    data = parse_netperf_run(path)
    if 'simtime' in data:
        t = strftime("%H:%M:%S", gmtime(data['simtime']))
    else:
        t = ''

    tp = fmt_tp(data.get('throughput', ''))
    latMean = fmt_lat(data.get('latenyMean', ''))
    latTail = fmt_lat(data.get('latenyTail', ''))
    print('  %s & %s & %s & %s & %s & %s & %s \\\\' % (h_l, nic_l, net_l,
        tp, latMean, latTail, t))
