#!/bin/bash
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

###########################################################################
# This script runs dctcp experiment in standalone ns-3
# 
##### build dctcp-cwnd-devred.cc example in ns-3
##### cp examples/tcp/dctcp-cwnd-devred.cc scratch/
##### ./waf

##### ./ns3-dctcp.sh [num_core] 


EHSIM_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/../../..)"
NS3_BASE="$EHSIM_BASE/sims/external/ns-3"
OUTDIR_BASE="$EHSIM_BASE/experiments/pyexps"

cd $NS3_BASE
k_start=0
k_end=199680
k_step=16640
mtus="4000"

# This is the RTT
latencies="50us"
cores=$1

echo $cores

proc=0
pids=""

cleanup() {
    echo Cleaning up
    for p in $pids ; do
        kill $p &>/dev/null
    done

    sleep 1
    for p in $pids ; do
        kill -KILL $p &>/dev/null
    done

}

sighandler() {
    echo "Caught Interrupt, aborting...."
    cleanup
    exit 1
}


trap "sighandler" SIGINT

#for k in $(seq $k_start $k_step $k_end)
for lat in $latencies
do
    for m in $mtus
    do
        #echo $k
        #for m in 1500 4000 9000 # MTU size
        for k in $(seq $k_start $k_step $k_end)
        do
            echo "latency: $lat MtU: $m  K: $k  "
            ./cosim-dctcp-run.sh $k $m $lat &
            pid=$!
            pids="$pids $pid"
            proc=$(($proc + 1))
            
            if [ $proc -eq $cores ]; then
                for p in $pids; do
                    wait $p
                done
                proc=0
                pids=""

            fi
        done
    done
done

for p in $pids; do
    wait $p
done

