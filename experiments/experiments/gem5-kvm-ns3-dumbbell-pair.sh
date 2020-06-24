#!/bin/bash

source common-functions.sh

init_out gem5-kvm-ns3-dumbbell-pair $1
run_corundum_bm a
run_corundum_bm b
sleep 0.5
run_ns3_dumbbell ab "a" "b"
run_gem5 a a build/qemu-pair-server.tar X86KvmCPU a
run_gem5 b b build/gem5-pair-client.tar X86KvmCPU b
client_pid=$!
wait $client_pid
cleanup
