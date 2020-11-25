#!/bin/bash

##### build dctcp-modes.cc example in ns-3
##### cp cp examples/tcp/dctcp-modes.cc scratch/dctcp-modes.cc
##### ./waf

##### ./ns3-dctcp.sh [num_core] 


EHSIM_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/../..)"
NS3_BASE="$EHSIM_BASE/ns-3"
OUTDIR_BASE="$EHSIM_BASE/experiments/pyexps"

cd $NS3_BASE
k_start=0
#k_end=199680
k_end=0
k_step=8320
#mtus="1500 4000 9000"
mtus="1500"
cores=$1

echo $cores

proc=0
pids=""

#for k in $(seq $k_start $k_step $k_end)
for m in $mtus
do
    #echo $k
    #for m in 1500 4000 9000 # MTU size
    for k in $(seq $k_start $k_step $k_end)
    do
        echo "MtU: $m  K: $k  "
        ./cosim-dctcp-run.sh $k $m 
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
