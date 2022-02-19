#!/bin/bash -eux
set -eux

apt-get -y install build-essential git libnuma-dev libgmp-dev bc python

cd /root/
wget http://fast.dpdk.org/rel/dpdk-18.11.8.tar.gz
tar xf dpdk-18.11.8.tar.gz
cd dpdk-stable-18.11.8
make -j`nproc` install T=x86_64-native-linuxapp-gcc DESTDIR=/root/dpdk
cd ..
rm -rf dpdk-*

git clone https://github.com/tcp-acceleration-service/tas.git /root/tas
cd /root/tas
make -j`nproc` RTE_SDK=/root/dpdk

git clone https://github.com/FreakyPenguin/benchmarks.git /root/tasbench
cd /root/tasbench/micro_rpc
make echoserver_linux testclient_linux TAS_CODE="/root/tas"

echo "blacklist i40e" > /etc/modprobe.d/i40e_bl.conf
