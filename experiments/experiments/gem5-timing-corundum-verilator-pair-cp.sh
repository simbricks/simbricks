#!/bin/bash

source common-functions.sh

init_out gem5-timing-corundum-verilator-pair-cp $1

echo "Restoring from checkpoint"

# then run with timing CPU
run_corundum_verilator a_cp
run_corundum_verilator b_cp
sleep 2
run_wire ab_cp a_cp b_cp
sleep 1
run_gem5 a_cp a_cp build/gem5-pair-server-cp.tar TimingSimpleCPU server "-r 0 --cosim-sync"
sleep 1
run_gem5 b_cp b_cp build/gem5-pair-client-cp.tar TimingSimpleCPU client "-r 0 --cosim-sync"
client_pid=$!
wait $client_pid
cleanup

