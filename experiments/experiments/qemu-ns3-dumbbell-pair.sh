#!/bin/bash

source common-functions.sh

init_out qemu-ns3-dumbbell-pair $1
run_corundum_bm a
run_corundum_bm b
sleep 0.5
#run_ns3_dumbbell ab "a" "b" "--LinkRate=10Mbps --LinkLatency=0"
run_ns3_dumbbell ab "a" "b" "--LinkRate=10Mb/s --LinkLatency=0"
run_qemu a a build/qemu-pair-server.tar
run_qemu b b build/qemu-pair-client.tar
client_pid=$!
wait $client_pid
cleanup
