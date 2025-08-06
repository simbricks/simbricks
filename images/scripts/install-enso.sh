#!/bin/bash -eux
set -eux

apt-get -y update
apt-get -y install build-essential g++-9 git libnuma-dev gdb rsync \
    linux-headers-$(uname -r) linux-modules-extra-$(uname -r) \
    bc libelf-dev kmod pkg-config meson

cd /root/
git clone https://github.com/crossroadsfpga/enso
cd /root/enso
git checkout simbricks-24.04

./setup.sh --no-quartus
