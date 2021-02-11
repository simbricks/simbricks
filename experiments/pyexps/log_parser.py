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
import os
import pathlib
import shutil
import json

# How to use
# $ python3 parser.py ../out/qemu-wire-ib-TCPs-1.json 
#

log_file = sys.argv[1]
log = open(log_file, 'r')

curdir = pathlib.Path().absolute()

exp_log = json.load(log)

#Name, starting & ending time
exp_name = exp_log['exp_name']
tooutdir = f'../out/{exp_name}'
outdir = os.path.join(curdir, tooutdir)

if not os.path.exists(outdir):
    raise Exception("no such directory")

start_end_path = os.path.join(outdir, 'start_end.txt')
start_end_file = open(start_end_path, 'w')
start_end_file.write('start time: ' + str(exp_log["start_time"]) + '\n')
start_end_file.write('end time: ' + str(exp_log["end_time"]) + '\n')
start_end_file.write('success: ' + str(exp_log["success"]))
start_end_file.close()

for i in exp_log["sims"]:
    #print(i)
    simdir = os.path.join(outdir, i)
    sim_out_file = open(simdir, 'w')
    
    for j in exp_log["sims"][i]:
        #print(j)
        sim_out_file.write( j + '\n')

        if (j == 'class' ):
            sim_out_file.write(exp_log["sims"][i][j] + '\n')
        
        else:
            
            for k in exp_log["sims"][i][j]:
                sim_out_file.write(k + '\n')
    
    sim_out_file.close()
