#!/bin/bash

source common-functions.sh

init_out gem5-timing-corundum-verilator-switched-8-nocp $1
run_corundum_verilator a
run_corundum_verilator b
run_corundum_verilator c
run_corundum_verilator d
run_corundum_verilator e
run_corundum_verilator f
run_corundum_verilator g
run_corundum_verilator h
run_corundum_verilator i
sleep 0.5
run_ns3_dumbbell bridge "a" "b c d e f g h i" "--LinkRate=100Mb/s --LinkLatency=0"
run_gem5 a a build/qemu-pair-server.tar TimingSimpleCPU server "--cosim-sync"

client_pids=""
run_gem5 b b build/gem5-pair-client-8-1.tar TimingSimpleCPU client "--cosim-sync"
client_pids="$client_pids $!"
run_gem5 c c build/gem5-pair-client-8-2.tar TimingSimpleCPU client "--cosim-sync"
client_pids="$client_pids $!"
run_gem5 d d build/gem5-pair-client-8-3.tar TimingSimpleCPU client "--cosim-sync"
client_pids="$client_pids $!"
run_gem5 e e build/gem5-pair-client-8-4.tar TimingSimpleCPU client "--cosim-sync"
client_pids="$client_pids $!"
run_gem5 f f build/gem5-pair-client-8-5.tar TimingSimpleCPU client "--cosim-sync"
client_pids="$client_pids $!"
run_gem5 g g build/gem5-pair-client-8-6.tar TimingSimpleCPU client "--cosim-sync"
client_pids="$client_pids $!"
run_gem5 h h build/gem5-pair-client-8-7.tar TimingSimpleCPU client "--cosim-sync"
client_pids="$client_pids $!"
run_gem5 i i build/gem5-pair-client-8-8.tar TimingSimpleCPU client "--cosim-sync"
client_pids="$client_pids $!"

for p in $client_pids; do
    wait $p
done

cleanup

