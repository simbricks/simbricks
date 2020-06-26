#!/bin/bash

source common-functions.sh

init_out gem5-timing-corundum-verilator-switched-1-nocp $1

# then run with timing CPU
run_corundum_verilator a
run_corundum_verilator b
sleep 0.5
run_ns3_dumbbell bridge "a" "b" "--LinkRate=100Mb/s --LinkLatency=100us"
run_gem5 a a build/qemu-pair-server.tar TimingSimpleCPU server "--cosim-sync"
run_gem5 b b build/gem5-pair-client.tar TimingSimpleCPU client "--cosim-sync"
client_pid=$!
wait $client_pid
cleanup

