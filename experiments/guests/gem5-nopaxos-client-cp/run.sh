#!/bin/bash
/sbin/m5 checkpoint
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 10.1.0.100/24 dev eth0
sleep 4
/root/nopaxos/bench/client -c /root/nopaxos.config -m nopaxos -n 2000
/sbin/m5 exit
