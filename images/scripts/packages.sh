#!/bin/bash
apt-get update
mount 1>&2
apt-get -y install \
    ntp \
    nfs-common \
    iperf \
    netperf \
    netcat \
    make \
    git \
    pkg-config \
    libevent-dev \
    libunwind-dev \
    autoconf \
    automake \
    libtool \
    g++ \
    libssl-dev \
    ethtool \
