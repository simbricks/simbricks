#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 10.100.0.2/24 dev eth0
sleep 2
ping -c 5 10.100.0.1
poweroff -f
