#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 192.168.64.2/24 dev eth0
sleep 2
iperf -c 192.168.64.1 -u -b 150m
m5 exit
