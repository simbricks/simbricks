#!/bin/bash

source common-functions.sh

init_out gem5-timing-corundum-bm-ns3-nopaxos $1

# first run to checkpoint with fast CPU
run_corundum_bm c0
run_corundum_bm r0
run_corundum_bm r1
run_corundum_bm r2
sleep 0.5
run_ns3_sequencer nopaxos "c0" "r0 r1 r2"
run_gem5 r0 r0 build/gem5-nopaxos-replica-0-cp.tar X86KvmCPU r0
run_gem5 r1 r1 build/gem5-nopaxos-replica-1-cp.tar X86KvmCPU r1
run_gem5 r2 r2 build/gem5-nopaxos-replica-2-cp.tar X86KvmCPU r2
run_gem5 c0 c0 build/gem5-nopaxos-client-cp.tar X86KvmCPU c0
client_pid=$!
wait $client_pid
cleanup

echo "took checkpoint successfully"

# then run with timing CPU
run_corundum_bm c0_cp
run_corundum_bm r0_cp
run_corundum_bm r1_cp
run_corundum_bm r2_cp
sleep 0.5
run_ns3_sequencer nopaxos_cp "c0_cp" "r0_cp r1_cp r2_cp"
run_gem5 r0_cp r0_cp build/gem5-nopaxos-replica-0-cp.tar TimingSimpleCPU r0 "-r 0"
run_gem5 r1_cp r1_cp build/gem5-nopaxos-replica-1-cp.tar TimingSimpleCPU r1 "-r 0"
run_gem5 r2_cp r2_cp build/gem5-nopaxos-replica-2-cp.tar TimingSimpleCPU r2 "-r 0"
run_gem5 c0_cp c0_cp build/gem5-nopaxos-client-cp.tar TimingSimpleCPU c0 "-r 0"
client_pid=$!
wait $client_pid
cleanup

