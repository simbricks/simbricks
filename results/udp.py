import sys
import os
import pathlib
import shutil
import json

if len(sys.argv) != 2:
    print('Usage: udp.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'

# FIXME: dropped 120 because it looks off
types_of_bw = [0, 20, 40, 60, 80, 100, 140, 200, 500, 800, 1000]


for bw in types_of_bw:
    log_path = '%sgt-ib-wire-UDPs-%dm-1.json' % (basedir, bw)
    if os.path.exists(log_path):
        log = open(log_path, 'r')
        exp_log = json.load(log)
        start_time = exp_log["start_time"]
        end_time = exp_log["end_time"]
        diff_time = (end_time - start_time)/60 #min
        diff_time = str(diff_time)
    else:
        diff_time = ''

    print('%d\t%s' % (bw, diff_time))

    log.close()

