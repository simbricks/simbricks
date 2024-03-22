#!/bin/bash
export XDG_RUNTIME_DIR=/tmp/xdg
mkdir -p $2/rootfs
mkdir -p $2/root
tar -C $2/rootfs -xf $1
patch -d $2/rootfs -p1 <`pwd`/kvm-group.patch

cd $2
runc spec --rootless
