import itertools
import sys
import utils.iperf

if len(sys.argv) != 2:
    print('Usage: dctcp.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'

types_of_host = ['gt', 'qt']
mtus = [1500, 4000]
max_k = 199680
k_step = 16640

configs = list(itertools.product(types_of_host, mtus))
confignames = [h + '-' + str(mtu) for h, mtu in configs]
print('\t'.join(['threshold'] + confignames))


for k_val in range(0, max_k + 1, k_step):
    line = [str(k_val)]
    for h, mtu in configs:
        path_pat = '%s%s-ib-dumbbell-DCTCPm%d-%d' % (basedir, h, k_val, mtu)
        res = utils.iperf.parse_iperf(path_pat)

        if res['avg'] is None:
            line.append('')
            continue

        tp = res['avg']
        # TP * (MTU + ETH(14(MAC) + 24(PHY))) / (MTU - IP (20) - TCP w/option (24))
        tp_calib = tp * (mtu + (14 + 24)) / (mtu - 20 - 24)
        line.append('%.2f' % (tp_calib))

    print('\t'.join(line))
