import glob
import json
import os
import re
import sys

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

    runk = (mtu, k)
    clients = runmap.get(runk, {})

    with open(f, 'r', encoding='utf-8') as f:
        clients['host.client.' + m.group(3)] = {'stdout': f.readlines()}
    runmap[runk] = clients

for ((mtu, k), clients) in runmap.items():
    ofn = f'{outdir}tb-ib-dumbbell-DCTCPm{k}-{mtu}-1.json'
    data = {'sims': clients}
    with open(ofn, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile)
