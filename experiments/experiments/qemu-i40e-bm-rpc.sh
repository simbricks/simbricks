#!/bin/bash

source common-functions.sh

init_out qemu-i40e-bm-rpc $1
run_i40e_bm a
run_i40e_bm b
sleep 0.5
run_wire ab a b
run_qemu a a build/qemu-i40e-rpc-server.tar tas
run_qemu b b build/qemu-i40e-rpc-client.tar tas
client_pid=$!
wait $client_pid
cleanup
