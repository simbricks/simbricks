#!/bin/bash -eux

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
