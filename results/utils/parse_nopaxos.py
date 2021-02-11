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

import json
import re
import os

def parse_nopaxos_run(num_c, seq, path):
    
    ret = {}
    ret['throughput'] = None
    ret['latency'] = None

    tp_pat = re.compile(r'(.*)Completed *([0-9\.]*) requests in *([0-9\.]*) seconds')
    lat_pat = re.compile(r'(.*)Average latency is *([0-9\.]*) ns(.*)')
    if not os.path.exists(path):
        return ret
    
    f_log = open(path, 'r')
    log = json.load(f_log)

    total_tput = 0
    total_avglat = 0
    for i in range(num_c):
        sim_name = f'host.client.{i}'
        #print(sim_name)
        
        # in this host log stdout
        for j in log["sims"][sim_name]["stdout"]:
            #print(j)
            m_t = tp_pat.match(j)
            m_l = lat_pat.match(j)
            if m_l:
                #print(j)
                lat = float(m_l.group(2)) / 1000 # us latency
                #print(lat)
                total_avglat += lat
                
            if m_t:
                
                n_req = float(m_t.group(2))
                n_time = float(m_t.group(3))
                total_tput += n_req/n_time


    avglat = total_avglat/num_c
    #print(avglat)    
    #print(total_tput)
    ret['throughput'] = total_tput
    ret['latency'] = avglat

    return ret
