#!/bin/bash

source common-functions.sh

init_out qemu-corundum-bm-echo $1
run_corundum_bm a
run_corundum_bm b
sleep 2
run_wire ab a b
run_qemu a a build/qemu-echo-server.tar
run_qemu b b build/qemu-echo-client.tar
client_pid=$!
wait $client_pid
cleanup
