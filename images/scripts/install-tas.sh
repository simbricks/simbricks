#!/bin/bash -eux
set -eux

apt-get -y install libnuma-dev libgmp-dev bc python

cd /root/
wget http://deb.debian.org/debian/pool/main/d/dpdk/dpdk_18.11.8.orig.tar.xz
tar xf dpdk_18.11.8.orig.tar.xz
cd dpdk-stable-18.11.8
make -j4 install T=x86_64-native-linuxapp-gcc DESTDIR=/root/dpdk
cd ..
rm -rf dpdk-*

git clone https://github.com/tcp-acceleration-service/tas.git /root/tas
cd /root/tas
make -j4 RTE_SDK=/root/dpdk

git clone https://github.com/FreakyPenguin/benchmarks.git /root/tasbench
cd /root/tasbench/micro_rpc
make echoserver_linux testclient_linux TAS_CODE="/root/tas" 

echo "blacklist i40e" > /etc/modprobe.d/i40e_bl.conf
