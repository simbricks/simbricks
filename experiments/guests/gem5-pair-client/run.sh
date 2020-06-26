#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 192.168.64.2/24 dev eth0
sleep 2
iperf -l 1M -w 1M -c 192.168.64.1 -P 16
m5 exit
