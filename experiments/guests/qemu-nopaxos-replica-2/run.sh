#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 10.1.0.3/24 dev eth0
ping -c 5 10.1.0.1
/root/nopaxos/bench/replica -c /root/nopaxos.config -i 2 -m nopaxos
poweroff
