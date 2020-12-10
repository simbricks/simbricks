import itertools
import sys
import utils.iperf

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

for (ht,nt,lab) in configs:
    cols = [str(lab)]
    for lat in lats:
        path_pat = '%spcilat-%s-%s-switch-%d' % (basedir, ht, nt, lat)
        res = utils.iperf.parse_iperf(path_pat)

        if res['avg'] is None:
            cols.append('')
        else:
            cols.append(str(res['avg']))

    print('\t'.join(cols))
