#!/bin/bash

source common-functions.sh

init_out qemu-ns3-nopaxos-verilator $1
run_corundum_verilator c0
run_corundum_verilator r0
run_corundum_verilator r1
run_corundum_verilator r2
sleep 0.5
run_ns3_sequencer nopaxos "c0" "r0 r1 r2"
run_qemu r0 r0 build/qemu-nopaxos-replica-0.tar
sleep 1
run_qemu r1 r1 build/qemu-nopaxos-replica-1.tar
run_qemu r2 r2 build/qemu-nopaxos-replica-2.tar
sleep 1
run_qemu c0 c0 build/qemu-nopaxos-client.tar
client_pid=$!
wait $client_pid
cleanup
