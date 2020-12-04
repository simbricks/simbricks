import glob
import json
import os
import fnmatch
import re
import itertools
import sys

def parse_iperf_run(data, skip=1, use=8):
    tp_pat = re.compile(r'\[ *\d*\] *([0-9\.]*)- *([0-9\.]*) sec.*Bytes *([0-9\.]*) Gbits.*')
    tps_time = {}
    for hn in fnmatch.filter(data['sims'].keys(), 'host.client.*'):
        sim = data['sims'][hn]
        for l in sim['stdout']:
            m = tp_pat.match(l)
            if not m:
                continue

            time = int(float(m.group(1)))
            if time < skip:
                continue
            if time >= skip + use:
                continue

            if not time in tps_time:
                tps_time[time] = []

            tps_time[time].append(float(m.group(3)))

    tps = []
    for t in sorted(tps_time.keys()):
        x = sum(tps_time[t])
        tps.append(x)


    if len(tps) == 0:
        return None
    return sum(tps) / len(tps)

def parse_iperf(basename, skip=1, use=8):
    runs = []
    for path in glob.glob(basename + '-*.json'):
        if path == basename + '-0.json':
            # skip checkpoints
            continue

        with open(path, 'r') as f:
            data = json.load(f)
        result = parse_iperf_run(data, skip, use)
        if result is not None:
            runs.append(result)

    if not runs:
        return {'avg': None, 'min': None, 'max': None}
    else:
        return {'avg': sum(runs) / len(runs), 'min': min(runs),
                'max': max(runs)}
    result = {}
