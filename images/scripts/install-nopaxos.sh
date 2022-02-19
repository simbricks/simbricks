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
    pkg-config

git clone https://github.com/google/protobuf.git /tmp/protobuf
cd /tmp/protobuf
./autogen.sh
./configure
make -j4
make install
ldconfig

mkdir -p /root
git clone https://github.com/nicklijl/simbricks-nopaxos.git /root/nopaxos
cd /root/nopaxos
make -j4

 mv /tmp/input/nopaxos.config /root/nopaxos.config
