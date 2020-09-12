#!/bin/bash
export HOME=/root
export LANG=en_US
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"

mount -t proc proc /proc
mount -t sysfs sysfs /sys
mkdir -p /dev/hugepages
mount -t hugetlbfs nodev /dev/hugepages
#-o pagesize=1G
mkdir -p /dev/shm
mount -t tmpfs tmpfs /dev/shm
#find /sys/
#modprobe vfio-pci
#echo 1 >/sys/module/vfio/parameters/enable_unsafe_noiommu_mode
insmod /root/mtcp/dpdk/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko
/root/mtcp/dpdk/usertools/dpdk-devbind.py -b igb_uio 0000:00:02.0
find /sys/devices/system/node/node0/hugepages/
#echo 4> /sys/devices/system/node/node0/hugepages/hugepages-1048576kB/nr_hugepages
echo 4096 > /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages
#echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
insmod /root/mtcp/dpdk-iface-kmod/dpdk_iface.ko
/root/mtcp/dpdk-iface-kmod/dpdk_iface_main
ip link
ip link set dev dpdk0 up
ip addr add 192.168.64.1/24 dev dpdk0



#cd /root/mtcp
#patch -p1 </tmp/guest/mtcp.patch
#export RTE_SDK=/root/mtcp/dpdk
#export RTE_TARGET=x86_64-native-linuxapp-gcc
#
#make -C dpdk install T=$RTE_TARGET
#make

cd /root/tasbench/micro_rpc
#make clean
#make echoserver_mtcp MTCP_BASE="/root/mtcp" TAS_CODE="/root/tas"
#rm -rf /var/run/dpdk /dev/hugepages/*
./echoserver_mtcp 1234 1 /tmp/guest/mtcp.conf 128 1024
poweroff
