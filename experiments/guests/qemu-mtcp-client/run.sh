#!/bin/bash
export HOME=/root
export LANG=en_US
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"

mount -t proc proc /proc
mount -t sysfs sysfs /sys
mkdir -p /dev/hugepages
mount -t hugetlbfs nodev /dev/hugepages
mkdir -p /dev/shm
mount -t tmpfs tmpfs /dev/shm
insmod /root/mtcp/dpdk/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko
/root/mtcp/dpdk/usertools/dpdk-devbind.py -b igb_uio 0000:00:02.0
echo 4096 > /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages
insmod /root/mtcp/dpdk-iface-kmod/dpdk_iface.ko
/root/mtcp/dpdk-iface-kmod/dpdk_iface_main
ip link
ip link set dev dpdk0 up
ip addr add 192.168.64.2/24 dev dpdk0

cd /root/tasbench/micro_rpc
./testclient_mtcp 192.168.64.1 1234 1 /tmp/guest/mtcp.conf 1024 1 1
poweroff
