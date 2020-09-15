#!/bin/bash
mount -t proc proc /proc
mount -t sysfs sysfs /sys
modprobe i40e
sysctl -w net.core.busy_poll=50
sysctl -w net.core.busy_read=50
ip link set dev eth0 up
ip addr add 192.168.64.1/24 dev eth0
ethtool -K eth0 tso off
iperf -s -l 1M -w 1M -P 4
poweroff -f
