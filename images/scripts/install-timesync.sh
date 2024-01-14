#!/bin/bash -eux

ls -l /bin/sh
cd /bin
rm sh
ln -s bash sh

apt-get update
apt-get -y install \
  autoconf2.69 \
  bison \
  build-essential \
  chrony \
  cmake \
  file \
  git \
  libncurses-dev \
  linuxptp \
  yarnpkg

wget -O /usr/local/bin/bazel \
  https://github.com/bazelbuild/bazelisk/releases/download/v1.19.0/bazelisk-linux-amd64

GOVER=1.16.5
cd /tmp
wget https://go.dev/dl/go${GOVER}.linux-amd64.tar.gz
tar -C /usr/local -xzf go${GOVER}.linux-amd64.tar.gz
rm -f go${GOVER}.linux-amd64.tar.gz
export PATH=/usr/local/go/bin:$PATH

export GOPATH=/root/go
go env -w GOPATH=$GOPATH

ln -s /usr/bin/yarnpkg /usr/bin/yarn
for f in autoconf autoheader autom4te autoreconf autoscan autoupdate ifnames
do
  cp /usr/bin/${f}2.69 /usr/bin/${f}
done


mkdir -p $GOPATH/src/github.com/cockroachdb/
cd $GOPATH/src/github.com/cockroachdb/
git clone https://github.com/fabianlindfors/cockroach.git
cd cockroach
sed -i -e 's/echo go install/echo $(GO_INSTALL)/g' Makefile
make build
make install

mkdir -p /root/cockroach/certs /root/cockroach/safedir \
  /root/cockroach/server-certs
cockroach cert create-ca \
  --certs-dir=/root/cockroach/certs \
  --ca-key=/root/cockroach/safedir/ca.key

for i in `seq 1 32` ; do
  ip=10.0.0.$i
  cockroach cert create-node $ip \
    --certs-dir=/root/cockroach/certs \
    --ca-key=/root/cockroach/safedir/ca.key
  mv /root/cockroach/certs/node.crt /root/cockroach/server-certs/$ip.crt
  mv /root/cockroach/certs/node.key /root/cockroach/server-certs/$ip.key
done

cockroach cert create-client \
  root \
  --certs-dir=/root/cockroach/certs \
  --ca-key=/root/cockroach/safedir/ca.key

