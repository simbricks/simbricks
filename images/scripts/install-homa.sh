#!/bin/bash -eux

apt-get update
apt-get -y install \
    autoconf \
    automake \
    build-essential \
    g++ \
    git \
    libevent-dev \
    libssl-dev \
    libtool \
    libunwind-dev \
    make \
    vim \
    pkg-config

mkdir -p /root
#git clone https://github.com/PlatformLab/HomaModule.git /root/homa
cp -r /tmp/input/homa /root/homa
cd /root/homa
#git checkout linux_5.17.7
cd /root/homa/util
make