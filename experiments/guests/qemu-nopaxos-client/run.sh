#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 10.1.0.100/24 broadcast 10.1.0.255 dev eth0
/root/nopaxos/bench/client -c /root/nopaxos.config -m nopaxos -n 1000
poweroff -f
