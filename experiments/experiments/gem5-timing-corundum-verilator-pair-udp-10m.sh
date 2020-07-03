#!/bin/bash

source common-functions.sh

init_out gem5-timing-corundum-verilator-pair-udp-10m $1

run_corundum_verilator a
run_corundum_verilator b
sleep 0.5
run_wire ab a b
run_gem5 a a build/gem5-pair-server-udp.tar TimingSimpleCPU server "--cosim-sync"
run_gem5 b b build/gem5-pair-client-udp-10m.tar TimingSimpleCPU client "--cosim-sync"
client_pid=$!
wait $client_pid
cleanup
