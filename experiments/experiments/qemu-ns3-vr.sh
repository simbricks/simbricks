#!/bin/bash

source common-functions.sh

init_out qemu-ns3-vr $1
run_corundum_bm c0
run_corundum_bm r0
run_corundum_bm r1
run_corundum_bm r2
sleep 0.5
run_ns3_sequencer vr "c0" "r0 r1 r2"
run_qemu r0 r0 build/qemu-vr-replica-0.tar
sleep 5
run_qemu r1 r1 build/qemu-vr-replica-1.tar
run_qemu r2 r2 build/qemu-vr-replica-2.tar
sleep 5
run_qemu c0 c0 build/qemu-vr-client.tar
client_pid=$!
wait $client_pid
cleanup
