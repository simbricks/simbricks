#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 192.168.64.2/24 dev eth0
sleep 2
sleep 10
m5 exit
