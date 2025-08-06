#!/bin/bash
set -e
mkdir -p sims/external/qemu-new/build/x86_64-softmmu/
rm -rf sims/external/qemu/build/pc-bios/{edk2-aarch64*,edk2-arm*}
mv sims/external/qemu/build/{qemu-img,qemu-system-x86_64,pc-bios} \
	sims/external/qemu-new/build/
mv sims/external/qemu/pc-bios/ \
	sims/external/qemu-new/
rm -rf sims/external/qemu
test -f .git && git submodule deinit -f sims/external/qemu
rm -rf .git/modules/sims/external/qemu
rm -rf sims/external/qemu
mv sims/external/qemu-new sims/external/qemu
ln -s /simbricks/sims/external/qemu/build/qemu-system-x86_64 \
	sims/external/qemu/build/x86_64-softmmu/qemu-system-x86_64
touch sims/external/qemu/ready
