#!/bin/bash

source common-functions.sh

init_out qemu-corundum-bm-switched-8 $1
run_corundum_bm a
run_corundum_bm b
run_corundum_bm c
run_corundum_bm d
run_corundum_bm e
run_corundum_bm f
run_corundum_bm g
run_corundum_bm h
run_corundum_bm i
sleep 0.5
run_ns3_dumbbell bridge "a" "b c d e f g h i" "--LinkRate=100Mb/s --LinkLatency=0"
run_qemu a a build/qemu-pair-server.tar
sleep 10

client_pids=""
run_qemu b b build/qemu-pair-client-8-1.tar
client_pids="$client_pids $!"
run_qemu c c build/qemu-pair-client-8-2.tar
client_pids="$client_pids $!"
run_qemu d d build/qemu-pair-client-8-3.tar
client_pids="$client_pids $!"
run_qemu e e build/qemu-pair-client-8-4.tar
client_pids="$client_pids $!"
run_qemu f f build/qemu-pair-client-8-5.tar
client_pids="$client_pids $!"
run_qemu g g build/qemu-pair-client-8-6.tar
client_pids="$client_pids $!"
run_qemu h h build/qemu-pair-client-8-7.tar
client_pids="$client_pids $!"
run_qemu i i build/qemu-pair-client-8-8.tar
client_pids="$client_pids $!"

for p in $client_pids; do
    wait $p
done

cleanup
