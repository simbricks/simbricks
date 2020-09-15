#!/bin/bash
modprobe i40e
ip link set dev eth0 up
ip addr add 192.168.64.1/24 dev eth0

cd /root/tasbench/micro_rpc
./echoserver_linux 1234 1 /tmp/guest/mtcp.conf 1024 1024
poweroff -f
