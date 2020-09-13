#!/bin/bash

qemupath=`pwd`/../qemu/

# add our qemu to $PATH
export PATH="$qemupath:$qemupath/x86_64-softmmu/:$PATH"
exec ./packer "$@"
