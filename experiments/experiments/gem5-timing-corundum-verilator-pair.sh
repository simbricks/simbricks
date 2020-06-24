#!/bin/bash

source common-functions.sh

init_out gem5-timing-corundum-verilator-pair $1

# first run to checkpoint with fast CPU
run_corundum_verilator a
run_corundum_verilator b
sleep 0.5
run_wire ab a b
run_gem5 a a build/gem5-pair-server-cp.tar X86KvmCPU server
run_gem5 b b build/gem5-pair-client-cp.tar X86KvmCPU client
client_pid=$!
wait $client_pid
cleanup

echo "Took checkpoint successfully"

# then run with timing CPU
run_corundum_verilator a_cp
run_corundum_verilator b_cp
sleep 0.5
run_wire ab_cp a_cp b_cp
run_gem5 a_cp a_cp build/gem5-pair-server-cp.tar TimingSimpleCPU server "-r 0 --cosim-sync"
run_gem5 b_cp b_cp build/gem5-pair-client-cp.tar TimingSimpleCPU client "-r 0 --cosim-sync"
client_pid=$!
wait $client_pid
cleanup

