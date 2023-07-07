#!/bin/bash

### Ethernet interface accuracy
# This experimnets runs two ns-3 instances, each runs a host node connected by simbricks ethernet adapter to the other side
# Then it runs a single ns-3 instance with two host nodes connected inside ns-3

SB_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/../..)"
cd ../sims/external/ns-3
export LD_LIBRARY_PATH="build/lib/:$LD_LIBRARY_PATH"

RUN_DIR=$SB_BASE/experiments/out/accuracy
#RUN_DIR=/tmp/simbricks/ns3
rm -rf $RUN_DIR
mkdir -p $RUN_DIR


# Runs the SENDER host first
echo "run sender host"
./simbricks-run.sh simbricks-nicif-example --verbose --uxsoc=$RUN_DIR/uxsoc --shm=$RUN_DIR/shm --syncDelay=500000 --pollDelay=500000 --ethLatency=500000 --sync=1 --sync_mode=0 > $RUN_DIR/sender.out 2>&1 &

pid=$!
ALL_PIDS="$ALL_PIDS $pid"

sleep 1

# Runs the RECEIVER host
echo "run receiver host"
./simbricks-run.sh simbricks-netif-example --verbose --uxsoc=$RUN_DIR/uxsoc --syncDelay=500000 --pollDelay=500000 --ethLatency=500000 --sync=1 > $RUN_DIR/receiver.out 2>&1 &

# 
# 
pid=$!
ALL_PIDS="$ALL_PIDS $pid"

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

sleep 2



### Run single instance ns-3
echo "Run single instance ns-3"
./simbricks-run.sh packet-socket-apps --verbose > $RUN_DIR/single_ns3.out 2>&1

echo "parsing data"
cat $RUN_DIR/sender.out | awk '/Time:/ {print "Tx at: "$11}' > $RUN_DIR/sender.time
cat $RUN_DIR/receiver.out | awk '/time/ {print "Rx at: "$4}' > $RUN_DIR/receiver.time
cat $RUN_DIR/single_ns3.out | awk '{if($1 == "At") {print "Rx at: "$3} else if ($2 == "TX") {print "Tx at: "$10}}' > $RUN_DIR/single_ns3.time




echo "cleanup"
cleanup
