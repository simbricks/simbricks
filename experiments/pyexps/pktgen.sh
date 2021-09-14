#! /bin/bash

SIMBRICKS_DIR="/DS/endhost-networking/work/sim/hejing/simbricks"
RUN_DIR="/tmp/hejing-work/pktgen"
NUM_HOST=$1
ALL_PIDS=""
PKTGEN_PIDS=""
SWITCH_PIDS=""
# -inst num
run_pktgen(){
    echo "starting host $1"
    PKTGEN_EXE=/DS/endhost-networking/work/sim/hejing/simbricks/sims/net/pktgen/pktgen
    $PKTGEN_EXE -m 0 -S 500 -E 500 -n $1 -h $RUN_DIR/eth.$1 &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    PKTGEN_PIDS="$PKTGEN_PIDS $pid"
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


run_switch_dumbbell(){
    echo "Starting switch dumbbell"
    SWITCH_EXE=/DS/endhost-networking/work/sim/hejing/simbricks/sims/net/switch/net_switch
    args_0=""
    args_1=""
    iface=0
    half=$(($1/2))
    while [ $iface -lt $half ]
    do
        args_0="$args_0 -s $RUN_DIR/eth.$iface"
        #((iface+=2))
        ((iface+=1))
    done

    #iface=1

    #num_inc=$(($1+1))
    #while [ $iface -lt $num_inc ]
    while [ $iface -lt $1 ]
    do
        args_1="$args_1 -s $RUN_DIR/eth.$iface"
        #((iface+=2))
        ((iface+=1))
    done
    $SWITCH_EXE -m 0 -S 500 -E 500 \
    $args_0 -h $RUN_DIR/s0eth > $RUN_DIR/log.switch &

    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    SWITCH_PIDS="$SWITCH_PIDS $pid"
    sleep 1

    $SWITCH_EXE -m 0 -S 500 -E 500 \
    $args_1 -s $RUN_DIR/s0eth > $RUN_DIR/log.switch &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    SWITCH_PIDS="$SWITCH_PIDS $pid"

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
date
rm -rf $RUN_DIR
mkdir -p $RUN_DIR
r=0
while [ $r -lt $1 ]
do
    run_pktgen $r
    ((r++))
done

sleep 2
#run_switch $1
run_switch_dumbbell $1
#SWITCH_PID=$!

for p in $PKTGEN_PIDS ; do
    wait $p
done

echo "Pktgen Done, kill switch"
#kill -9 $SWITCH_PID

for p in $SWITCH_PIDS ; do
    kill -9 $p
done
date