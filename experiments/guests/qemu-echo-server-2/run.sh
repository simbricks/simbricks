#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 10.100.0.4/24 dev eth0
sleep infinity
poweroff -f
