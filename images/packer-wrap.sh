#!/bin/bash

qemupath=`pwd`/../qemu/

# add our qemu to $PATH
export PATH="$qemupath:$qemupath/build/:$PATH"
exec ./packer "$@"
