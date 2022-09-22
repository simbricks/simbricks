#!/bin/bash -eux

set -eux

pushd /tmp/input
mv guestinit.sh /home/ubuntu/guestinit.sh
mv bzImage /boot/vmlinuz-5.15.69
mv config-5.15.69 /boot/
mv m5 /sbin/m5
update-grub
tar xf kheaders.tar.bz2 -C /
popd
rm -rf /tmp/input

apt-get update
apt-get -y install \
    iperf \
    iputils-ping \
    netperf \
    netcat \
    ethtool \
    tcpdump \
    pciutils \
    busybox \
    numactl
