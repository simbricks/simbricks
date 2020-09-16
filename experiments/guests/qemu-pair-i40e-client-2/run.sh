#!/bin/bash
mount -t proc proc /proc
mount -t sysfs sysfs /sys
#sysctl -w net.core.busy_poll=50
#sysctl -w net.core.busy_read=50
sysctl -w net.core.rmem_default=31457280
sysctl -w net.core.rmem_max=31457280
sysctl -w net.core.wmem_default=31457280
sysctl -w net.core.wmem_max=31457280
sysctl -w net.core.optmem_max=25165824
sysctl -w net.ipv4.tcp_mem="786432 1048576 26777216"
sysctl -w net.ipv4.tcp_rmem="8192 87380 33554432"
sysctl -w net.ipv4.tcp_wmem="8192 87380 33554432"

modprobe i40e
ethtool -G eth0 rx 4096 tx 4096
ethtool -K eth0 tso off
echo 13888 > /proc/sys/net/core/netdev_max_backlog
ip link set eth0 txqueuelen 13888
ip link set dev eth0 mtu 9000 up
ip addr add 192.168.64.3/24 dev eth0
sleep 2
iperf -l 32M -w 32M  -c 192.168.64.1 -i 1 -P 4
poweroff -f
