#!/bin/bash

source common-functions.sh

init_out gem5-kvm-corundum-bm-pair
run_corundum_bm a
run_corundum_bm b
sleep 0.5
run_wire ab a b
run_gem5 a a build/qemu-pair-server.tar X86KvmCPU a
run_gem5 b b build/gem5-pair-client.tar X86KvmCPU b
client_pid=$!
wait $client_pid
cleanup
