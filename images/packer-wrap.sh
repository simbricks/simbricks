#!/bin/bash

qemupath=`pwd`/../sims/external/qemu/

cores=`nproc`
if [ $cores -gt 32 ]
then
    #limit cores to 32
    cores=32
fi

mem=$(($cores * 512))
if [ $mem -lt 4096 ]
then
    # at least 4G memory
    mem=4096
fi

base_img=$1
outname=$2
pkrfile=$3
compressed=$4

mkdir -p input-$outname

# add our qemu to $PATH
export PATH="$qemupath:$qemupath/build/:$PATH"
./packer build \
    -var "cpus=$cores" \
    -var "memory=$mem" \
    -var "base_img=$base_img" \
    -var "outname=$outname" \
    -var "compressed=$compressed" \
    ${pkrfile}
rm -rf input-$outname
