#!/bin/bash
m5 checkpoint
modprobe i40e
ip link set dev eth0 up
ip addr add 192.168.64.2/24 dev eth0
ethtool -K eth0 tso off
sleep 2
iperf -l 1M -w 1M -c 192.168.64.1
m5 exit
