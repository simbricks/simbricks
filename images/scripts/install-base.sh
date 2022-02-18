#!/bin/bash -eux

set -eux

pushd /tmp/input
mv guestinit.sh /home/ubuntu/guestinit.sh
mv bzImage /boot/vmlinuz-5.4.46
mv config-5.4.46 /boot/
mv m5 /sbin/m5
update-grub
tar xf kheaders.tar.bz2 -C /
popd
rm -rf /tmp/input
