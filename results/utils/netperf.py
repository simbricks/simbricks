import json
import re
import os

def parse_netperf_run(path):
    ret = {}

    if not os.path.exists(path):
        return ret
    with open(path, 'r') as f:
        data = json.load(f)

    ret['simtime'] = data['end_time'] - data['start_time']

    tph_pat = re.compile(r'Size\s*Size\s*Size\s*Time\s*Throughput.*')
    start = None
    i = 0
    lines = data['sims']['host.client.0']['stdout']
    for l in lines:
        if tph_pat.match(l):
            start = i
            break
        i += 1

    if start is not None:
        tp_line = lines[start + 3]
        tp_pat = re.compile(r'\s*\d*\s*\d*\s*\d*\s*[0-9\.]*\s*([0-9\.]*).*')
        m = tp_pat.match(tp_line)
        ret['throughput'] = float(m.group(1))



    lath_pat = re.compile(r'\s*Mean Latency.*')
    start = None
    i = 0
    lines = data['sims']['host.client.0']['stdout']
    for l in lines:
        if lath_pat.match(l):
            start = i
            break
        i += 1

    if start is not None:
        lat_line = lines[start + 1]
        lat_pat = re.compile(r'\s*([-0-9\.]*),([-0-9\.]*),([-0-9\.]*),([-0-9\.]*).*')
        m = lat_pat.match(lat_line)
        ret['latenyMean'] = float(m.group(1))
        ret['latenyTail'] = float(m.group(4))

    return ret
