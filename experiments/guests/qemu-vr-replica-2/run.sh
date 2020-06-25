#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 10.1.0.3/24 dev eth0
/root/nopaxos/bench/replica -c /root/nopaxos.config -i 2 -m vr
poweroff
