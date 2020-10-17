#!/bin/bash

source common-functions.sh

init_out qemu-i40e-bm-cc $1
run_i40e_bm a
run_i40e_bm b
run_i40e_bm c
sleep 0.5
run_ns3_bridge bridge "a b c"
run_qemu a a build/qemu-pair-i40e-server.tar
sleep 2
run_qemu b b build/qemu-pair-i40e-client.tar
run_qemu c c build/qemu-pair-i40e-client-2.tar
client_pid=$!
wait $client_pid
cleanup
