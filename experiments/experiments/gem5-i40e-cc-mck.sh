#!/bin/bash

source common-functions.sh

init_out gem5-i40e-cc checkpoint

# first run to checkpoint with fast CPU
run_i40e_bm a
run_i40e_bm b
run_i40e_bm c
sleep 2
run_ns3_bridge bridge "a b c"
run_gem5 a a build/gem5-pair-i40e-server.tar X86KvmCPU server "--cosim-type=i40e"
run_gem5 b b build/gem5-pair-i40e-client.tar X86KvmCPU client "--cosim-type=i40e"
run_gem5 c c build/gem5-pair-i40e-client-2.tar X86KvmCPU client2 "--cosim-type=i40e"
client_pid=$!
wait $client_pid
cleanup

echo "Took checkpoint successfully"
