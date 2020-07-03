#!/bin/bash

source common-functions.sh

init_out qemu-corundum-bm-switched-1 $1
run_corundum_bm a
run_corundum_bm b
sleep 0.5
run_ns3_dumbbell bridge "a" "b" "--LinkRate=100Mb/s --LinkLatency=0"
run_qemu a a build/qemu-pair-server.tar
sleep 10
run_qemu b b build/qemu-pair-client.tar
client_pid=$!
wait $client_pid
cleanup
