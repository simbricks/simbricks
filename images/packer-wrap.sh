#!/bin/bash

qemupath=`pwd`/../sims/external/qemu/

# add our qemu to $PATH
export PATH="$qemupath:$qemupath/build/:$PATH"
exec ./packer "$@"
