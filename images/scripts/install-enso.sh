#!/bin/bash -eux
set -eux

apt-get -y update
apt-get -y install build-essential git libnuma-dev gdb

cd /root/
git clone https://github.com/crossroadsfpga/enso
cd /root/enso
git checkout simbricks

./setup.sh --no-quartus
./scripts/sw_setup.sh 16384 32768 true
