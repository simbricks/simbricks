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
insmod /root/dpdk/lib/modules/5.4.46/extra/dpdk/igb_uio.ko
/root/dpdk/sbin/dpdk-devbind -b igb_uio 0000:00:02.0
echo 4096 > /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages

cd /root/tas
tas/tas --ip-addr=192.168.64.1/24 --fp-cores-max=1 --fp-no-ints &
sleep 3

cd /root/tasbench/micro_rpc
LD_PRELOAD=/root/tas/lib/libtas_interpose.so ./echoserver_linux 1234 1 /tmp/guest/mtcp.conf 1024 1024
poweroff -f
