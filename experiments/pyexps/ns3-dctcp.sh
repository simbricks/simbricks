#!/bin/bash

EHSIM_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/../..)"
NS3_BASE="$EHSIM_BASE/ns-3"

cd $NS3_BASE
mtu=1500
k_start=0
k_end=199680
#k_end=0
k_step=8320
cores=$1

echo $cores

proc=0
pids=""

for k in $(seq $k_start $k_step $k_end)
do
    #echo $k
    for m in 1500 4000 9000 # MTU size
    do
        echo "K: $k  MtU: $m"
        ./cosim-dctcp-run.sh $k $m &
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

for p in $pids; do
    wait $p
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
