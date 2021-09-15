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

# - number of hosts
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

# - number of hosts
# - number of middle switch
run_switch_chain(){
    echo "Starting switch chain"
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

    nswitch=0
    nums_dec=$(($2-1))
    
    while [ $nswitch -lt $2 ]
    do
        pswitch=$(($nswitch-1))
        #the first 
        if [ $nswitch -eq 0 ]
        then
            $SWITCH_EXE -m 0 -S 500 -E 500 \
            $args_0 -h $RUN_DIR/s0eth > $RUN_DIR/switch_${nswitch}.log &

            pid=$!
            ALL_PIDS="$ALL_PIDS $pid"
            SWITCH_PIDS="$SWITCH_PIDS $pid"
            sleep 1
        #the last
        elif [ $nswitch -eq $nums_dec ]      
        then
            $SWITCH_EXE -m 0 -S 500 -E 500 \
            $args_1 -s $RUN_DIR/s${pswitch}eth > $RUN_DIR/switch_${nswitch}.log &
            pid=$!
            ALL_PIDS="$ALL_PIDS $pid"
            SWITCH_PIDS="$SWITCH_PIDS $pid"
        else
            $SWITCH_EXE -m 0 -S 500 -E 500 \
            -s $RUN_DIR/s${pswitch}eth -h $RUN_DIR/s${nswitch}eth > $RUN_DIR/switch_${nswitch}.log &
            pid=$!
            ALL_PIDS="$ALL_PIDS $pid"
            SWITCH_PIDS="$SWITCH_PIDS $pid"
            sleep 1
        fi

        ((nswitch++))
    done

    return
}


# - number of hosts
# - number of layers should >= 2
run_switch_hierarchy(){
    echo "Starting switch hierarchy"
    SWITCH_EXE=/DS/endhost-networking/work/sim/hejing/simbricks/sims/net/switch/net_switch
    
    
    layer=1
    #leave switch
    iface=0
    
    while [ $iface -lt $1 ]
    do
        $SWITCH_EXE -m 0 -S 500 -E 500 \
        -h $RUN_DIR/s${layer}.$iface -s $RUN_DIR/eth.${iface}> $RUN_DIR/s${layer}.${iface}.log &
            
        pid=$!
        ALL_PIDS="$ALL_PIDS $pid"
        SWITCH_PIDS="$SWITCH_PIDS $pid"
        ((iface++))
    done 

    ((layer++))
    sleep 2
    #node switch
    while [ $layer -lt $2 ]
    do
        iface=0
        layer_dec=$(($layer-1))
        while [ $iface -lt $1 ]
        do
            $SWITCH_EXE -m 0 -S 500 -E 500 \
            -s $RUN_DIR/s${layer_dec}.$iface -h  $RUN_DIR/s${layer}.$iface > $RUN_DIR/s${layer}.${iface}.log &
            
            pid=$!
            ALL_PIDS="$ALL_PIDS $pid"
            SWITCH_PIDS="$SWITCH_PIDS $pid"
            ((iface++))
        done

        ((layer++))
        sleep 2
    done
    #root switch
    args=""
    iface=0
    layer_dec=$(($layer-1))
    while [ $iface -lt $1 ]
    do
        args="$args -s $RUN_DIR/s${layer_dec}.$iface"
        ((iface++))
    done
    $SWITCH_EXE -m 0 -S 500 -E 500 \
    $args > $RUN_DIR/root_switch.log &

    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    SWITCH_PIDS="$SWITCH_PIDS $pid"
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

echo -n "start: "
date +%s
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
#SWITCH_PID=$!
#run_switch_dumbbell $1
#run_switch_chain $1 $2
run_switch_hierarchy $1 $2

for p in $PKTGEN_PIDS ; do
    wait $p
done

echo "Pktgen Done, kill switch"
#kill -9 $SWITCH_PID

for p in $SWITCH_PIDS ; do
    kill -9 $p
done
echo -n "end: "
date +%s