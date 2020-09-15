#!/bin/bash
modprobe i40e
ip link set dev eth0 up
ip addr add 192.168.64.2/24 dev eth0

sleep 2
cd /root/tasbench/micro_rpc
./testclient_linux 192.168.64.1 1234 1 /tmp/guest/mtcp.conf 1024 1 128 2 0 8 &
sleep 25

poweroff -f
