#!/bin/bash

source common-functions.sh

init_out qemu-i40e-bm-mtcp $1
run_i40e_bm a
run_i40e_bm b
sleep 0.5
run_wire ab a b
run_qemu a a build/qemu-mtcp-server.tar mtcp
run_qemu b b build/qemu-mtcp-client.tar mtcp
#client_pid=$!
#wait $client_pid
sleep 20
cleanup
