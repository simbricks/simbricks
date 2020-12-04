import sys
import os
import re
import glob
import json

if len(sys.argv) != 2:
    print('Usage: generate_json.py OUTDIR')
    sys.exit(1)

cellsz = 208
outdir = sys.argv[1] + '/'
fn_pat = re.compile(r'(\d*)-(\d*)-(\d*).*')

runmap = {}

for f in glob.glob('testbed-results/*_*pktgap/*.txt'):
    bn = os.path.basename(f)
    m = fn_pat.match(bn)
    if not m:
        continue

    mtu = int(m.group(1))
    k = int(m.group(2)) * cellsz

    runk = (mtu,k)
    clients = runmap.get(runk, {})

    with open(f, 'r') as f:
        clients['host.client.' + m.group(3)] = {'stdout': f.readlines()}
    runmap[runk] = clients

for ((mtu, k), clients) in runmap.items():
    ofn = '%stb-ib-dumbbell-DCTCPm%d-%d-1.json' % (outdir, k, mtu)
    data = {'sims': clients}
    with open(ofn, 'w') as outfile:
        json.dump(data, outfile)
