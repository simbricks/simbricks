#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 10.1.0.1/24 dev eth0
ping -c 5 10.1.0.2
ping -c 5 10.1.0.3
/root/nopaxos/bench/replica -c /root/nopaxos.config -i 0 -m nopaxos
poweroff
