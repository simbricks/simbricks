#!/bin/bash

source common-functions.sh

init_out gem5-timing-corundum-verilator-pair-cp checkpoint

# first run to checkpoint with fast CPU
run_corundum_verilator a
run_corundum_verilator b
sleep 2
run_wire ab a b
sleep 1
run_gem5 a a build/gem5-pair-server-cp.tar X86KvmCPU server
sleep 1
run_gem5 b b build/gem5-pair-client-cp.tar X86KvmCPU client
client_pid=$!
wait $client_pid
cleanup

echo "Took checkpoint successfully"


