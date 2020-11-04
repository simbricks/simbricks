#!/bin/bash

source common-functions.sh

init_out qemu-ns3-nopaxos-endhost-sequencer $1
run_corundum_bm c0
run_corundum_bm r0
run_corundum_bm r1
run_corundum_bm r2
run_corundum_bm es
sleep 0.5
run_ns3_sequencer nopaxos "c0" "r0 r1 r2" "es"
run_qemu es es build/qemu-nopaxos-endhost-sequencer.tar nopaxos
run_qemu r0 r0 build/qemu-nopaxos-replica-0.tar nopaxos
sleep 1
run_qemu r1 r1 build/qemu-nopaxos-replica-1.tar nopaxos
run_qemu r2 r2 build/qemu-nopaxos-replica-2.tar nopaxos
sleep 1
run_qemu c0 c0 build/qemu-nopaxos-client.tar nopaxos
client_pid=$!
wait $client_pid
cleanup
