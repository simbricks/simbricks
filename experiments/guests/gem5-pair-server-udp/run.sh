#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 192.168.64.1/24 dev eth0
iperf -s -u
m5 exit
