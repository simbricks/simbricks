#!/bin/bash -eux

set -eux

apt-get -y install memcached libevent-dev
systemctl disable memcached.service

cd /tmp
wget https://launchpad.net/libmemcached/1.0/1.0.18/+download/libmemcached-1.0.18.tar.gz
tar xf libmemcached-1.0.18.tar.gz
cd libmemcached-1.0.18
./configure --enable-memaslap --disable-dtrace --prefix=/usr --enable-static \
    --disable-shared \
    CXXFLAGS='-fpermissive -pthread' \
    CFLAGS='-fpermissive -pthread' \
    LDFLAGS='-pthread' || (cat config.log ; exit 1)
make -j`nproc`
make -j`nproc` install

cd /tmp
rm -rf libmemcached-1.0.18 libmemcached-1.0.18.tar.gz
