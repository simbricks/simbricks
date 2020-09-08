#!/bin/bash

source common-functions.sh

init_out gem5-ns3-nopaxos-kvm-bm $1
run_corundum_bm c0
run_corundum_bm r0
run_corundum_bm r1
run_corundum_bm r2
sleep 0.5
run_ns3_sequencer nopaxos "c0" "r0 r1 r2"
run_gem5 r0 r0 build/qemu-nopaxos-replica-0.tar X86KvmCPU r0 "" nopaxos
sleep 1
run_gem5 r1 r1 build/qemu-nopaxos-replica-1.tar X86KvmCPU r1 "" nopaxos
run_gem5 r2 r2 build/qemu-nopaxos-replica-2.tar X86KvmCPU r2 "" nopaxos
sleep 1
run_gem5 c0 c0 build/gem5-nopaxos-client.tar X86KvmCPU c0 "" nopaxos
client_pid=$!
wait $client_pid
cleanup
