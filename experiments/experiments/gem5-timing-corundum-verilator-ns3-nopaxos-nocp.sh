#!/bin/bash

source common-functions.sh

init_out gem5-timing-corundum-verilator-ns3-nopaxos-nocp $1

run_corundum_verilator c0
run_corundum_verilator r0
run_corundum_verilator r1
run_corundum_verilator r2
sleep 0.5
run_ns3_sequencer nopaxos "c0" "r0 r1 r2"
run_gem5 r0 r0 build/gem5-nopaxos-replica-0-cp.tar TimingSimpleCPU r0 "--cosim-sync" nopaxos
run_gem5 r1 r1 build/gem5-nopaxos-replica-1-cp.tar TimingSimpleCPU r1 "--cosim-sync" nopaxos
run_gem5 r2 r2 build/gem5-nopaxos-replica-2-cp.tar TimingSimpleCPU r2 "--cosim-sync" nopaxos
run_gem5 c0 c0 build/gem5-nopaxos-client-cp.tar TimingSimpleCPU c0 "--cosim-sync" nopaxos
client_pid=$!
wait $client_pid
cleanup
