#!/bin/bash
mount -t proc proc /proc
mount -t sysfs sysfs /sys
sysctl -w net.core.rmem_default=31457280
sysctl -w net.core.rmem_max=31457280
sysctl -w net.core.wmem_default=31457280
sysctl -w net.core.wmem_max=31457280
sysctl -w net.core.optmem_max=25165824
sysctl -w net.ipv4.tcp_mem="786432 1048576 26777216"
sysctl -w net.ipv4.tcp_rmem="8192 87380 33554432"
sysctl -w net.ipv4.tcp_wmem="8192 87380 33554432"


m5 checkpoint
modprobe i40e
ethtool -G eth0 rx 4096 tx 4096
ethtool -K eth0 tso off
ip link set eth0 txqueuelen 13888
ip link set dev eth0 mtu 9000 up
ip addr add 192.168.64.1/24 dev eth0
iperf -s -l 32M -w 32M -P 8
m5 exit
