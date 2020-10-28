#!/bin/bash

source common-functions.sh

init_out qemu-corundum-bm-echo-switch $1
run_corundum_bm a
run_corundum_bm b
run_corundum_bm c
run_corundum_bm d
sleep 2
run_switch sw a b c d
run_qemu a a build/qemu-echo-server-0.tar
run_qemu b b build/qemu-echo-server-1.tar
run_qemu c c build/qemu-echo-server-2.tar
run_qemu d d build/qemu-echo-client.tar
client_pid=$!
wait $client_pid
cleanup
