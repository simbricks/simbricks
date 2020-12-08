import sys
import os
import pathlib
import shutil
import json

if len(sys.argv) != 2:
    print('Usage: udp_scale.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'
types_of_client = [1, 3, 7, 15, 31]
bw = 1000

for cl in types_of_client:
    log_path = '%sgt-ib-switch-UDPmicro-%d-%d-1.json' % (basedir, bw, cl)

    try:
        log = open(log_path, 'r')
    except:
        diff_time = ''
    else:
        exp_log = json.load(log)
        start_time = exp_log["start_time"]
        end_time = exp_log["end_time"]
        diff_time = (end_time - start_time)/60 #min
        diff_time = str(diff_time)
        log.close()

    print('%d\t%s' % (cl, diff_time))


