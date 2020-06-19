#!/bin/bash

source common-functions.sh

init_out qemu-corundum-verilator-pair
run_corundum_verilator a
run_corundum_verilator b
sleep 0.5
run_wire ab a b
run_qemu a a build/qemu-pair-server.tar
run_qemu b b build/qemu-pair-client.tar
client_pid=$!
wait $client_pid
cleanup
