#! /bin/bash

SIMBRICKS_DIR="/DS/endhost-networking/work/sim/hejing/simbricks"
RUN_DIR="/tmp/hejing-work/pktgen"
NUM_HOST=$1
ALL_PIDS=""
# -inst num
run_pktgen(){
    echo "starting host $1"
    PKTGEN_EXE=/DS/endhost-networking/work/sim/hejing/simbricks/sims/net/pktgen/pktgen
    $PKTGEN_EXE -m 0 -S 500 -E 500 -h $RUN_DIR/eth.$1 &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# -num host connected
run_switch(){
    echo "Starting switch"
    SWITCH_EXE=/DS/endhost-networking/work/sim/hejing/simbricks/sims/net/switch/net_switch
    args=""
    iface=0
    while [ $iface -lt $1 ]
    do
        args="$args -s $RUN_DIR/eth.$iface"
        ((iface++))
    done
    $SWITCH_EXE -m 0 -S 500 -E 500 \
    $args > $RUN_DIR/log.switch &

    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

cleanup() {
    echo "Cleaning up"

    for p in $ALL_PIDS ; do
        kill -KILL $p &>/dev/null
    done
    date
}

sighandler(){
    echo "caught Interrup, aborting..."
    cleanup
    date
    exit 1
}

trap "sighandler" SIGINT
rm -rf $RUN_DIR
mkdir -p $RUN_DIR
r=0
while [ $r -lt $1 ]
do
    run_pktgen $r
    ((r++))
done

sleep 2
run_switch $1