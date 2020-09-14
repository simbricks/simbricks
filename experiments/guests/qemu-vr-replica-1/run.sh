#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 10.1.0.2/24 dev eth0
/root/nopaxos/bench/replica -c /root/nopaxos.config -i 1 -m vr
poweroff -f
