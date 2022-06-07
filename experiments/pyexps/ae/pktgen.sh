#! /bin/bash

SB_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/../../..)"
RUN_DIR=$SB_BASE/experiments/out/pktgen/${1}h${2}b
#RUN_DIR=/tmp/simbricks/pktgen/${1}h${2}b
NUM_HOST=$1
ALL_PIDS=""
PKTGEN_PIDS=""
SWITCH_PIDS=""
# - inst num
# - pktgen bit rate
run_pktgen(){
    echo "starting host $1"
    PKTGEN_EXE=$SB_BASE/sims/net/pktgen/pktgen
    $PKTGEN_EXE -S 500 -E 500 -n $1 -h $RUN_DIR/eth.$1 -b $2 &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    PKTGEN_PIDS="$PKTGEN_PIDS $pid"
    return $pid
}

# -num host connected
run_switch(){
    echo "Starting switch"
    SWITCH_EXE=$SB_BASE/sims/net/switch/net_switch
    args=""
    iface=0
    while [ $iface -lt $1 ]
    do
        args="$args -s $RUN_DIR/eth.$iface"
        ((iface++))
    done
    $SWITCH_EXE -S 500 -E 500 \
    $args > $RUN_DIR/log.switch &

    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# - number of hosts
run_switch_dumbbell(){
    echo "Starting switch dumbbell"
    SWITCH_EXE=$SB_BASE/sims/net/switch/net_switch
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
    $SWITCH_EXE -S 500 -E 500 \
    $args_0 -h $RUN_DIR/s0eth > $RUN_DIR/log.switch &

    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    SWITCH_PIDS="$SWITCH_PIDS $pid"
    sleep 1

    $SWITCH_EXE -S 500 -E 500 \
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
    SWITCH_EXE=$SB_BASE/sims/net/switch/net_switch
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
            $SWITCH_EXE -S 500 -E 500 \
            $args_0 -h $RUN_DIR/s0eth > $RUN_DIR/switch_${nswitch}.log &

            pid=$!
            ALL_PIDS="$ALL_PIDS $pid"
            SWITCH_PIDS="$SWITCH_PIDS $pid"
            sleep 1
        #the last
        elif [ $nswitch -eq $nums_dec ]      
        then
            $SWITCH_EXE -S 500 -E 500 \
            $args_1 -s $RUN_DIR/s${pswitch}eth > $RUN_DIR/switch_${nswitch}.log &
            pid=$!
            ALL_PIDS="$ALL_PIDS $pid"
            SWITCH_PIDS="$SWITCH_PIDS $pid"
        else
            $SWITCH_EXE -S 500 -E 500 \
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

# - num host connected per Tor switch
# - num of Tor switch
run_switch_tor(){
    echo "Starting ToR switch"
    SWITCH_EXE=$SB_BASE/sims/net/switch/net_switch
    per_sw=$(($1/$2))
    nswitch=0
    host_idx=0

    # Run Tor switches
    while [ $nswitch -lt $2 ]
    do
        args=""
        iface=0
        while [ $iface -lt $per_sw ]
        do
            args="$args -s $RUN_DIR/eth.$host_idx"
            ((iface++))
            ((host_idx++))
        done

        # add interface connecting to root switch
        args="$args -h $RUN_DIR/s.${nswitch}"
        ((nswitch++))
        $SWITCH_EXE -S 500 -E 500 \
        $args > $RUN_DIR/log.tor${nswitch} &

        pid=$!
        SWITCH_PIDS="$SWITCH_PIDS $pid"
        ALL_PIDS="$ALL_PIDS $pid"
    done

    sleep 2

    # Run root switch
    echo "Run root switch"
    args=""
    iface=0
    while [ $iface -lt $nswitch ]
    do
        args="$args -s $RUN_DIR/s.$iface"
        ((iface++))
    done
    
    $SWITCH_EXE -S 500 -E 500 \
    $args > $RUN_DIR/log.rswitch &

    pid=$!
    SWITCH_PIDS="$SWITCH_PIDS $pid"
    ALL_PIDS="$ALL_PIDS $pid"
}

# - number of hosts
# - number of layers should >= 2
run_switch_hierarchy(){
    echo "Starting switch hierarchy"
    SWITCH_EXE=$SB_BASE/sims/net/switch/net_switch
    
    
    layer=1
    #leave switch
    iface=0
    
    while [ $iface -lt $1 ]
    do
        $SWITCH_EXE -S 500 -E 500 \
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
            $SWITCH_EXE -S 500 -E 500 \
            -s $RUN_DIR/s${layer_dec}.$iface -h  $RUN_DIR/s${layer}.$iface > $RUN_DIR/s${layer}.${iface}.log &
            
            pid=$!
            ALL_PIDS="$ALL_PIDS $pid"
            SWITCH_PIDS="$SWITCH_PIDS $pid"
            ((iface++))
        done

        ((layer++))
        sleep 2
    done
    sleep 2
    #root switch
    args=""
    iface=0
    layer_dec=$(($layer-1))
    while [ $iface -lt $1 ]
    do
        args="$args -s $RUN_DIR/s${layer_dec}.$iface"
        ((iface++))
    done
    $SWITCH_EXE -S 500 -E 500 \
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
    run_pktgen $r $2
    ((r++))
done

sleep 3
#run_switch $1
#SWITCH_PID=$!
#run_switch_dumbbell $1
#run_switch_chain $1 $2

if [ "$#" -lt 3 ]; then
    echo "usage: ./pktgen.sh [num_host] [bit_rate] [opt] [net_config] "
fi

if [ "$#" -eq 4 ]; then
    if [ $4 == "run_switch_hierarchy" ]; then
        echo "run switch hierarchy"
        run_switch_hierarchy $1 $3
    elif [ $4 == "run_switch_tor" ]; then
        echo "run switch tor $3"
        run_switch_tor $1 $3
    else
        echo "no matching config"
        cleanup
        exit 0
    fi
elif [ $3 == "run_switch" ]; then
    run_switch $1
elif [ $3 == "run_switch_dumbbell" ]; then
    run_switch_dumbbell $1
else    
    echo "no argument match"
    cleanup
    exit 0
fi

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