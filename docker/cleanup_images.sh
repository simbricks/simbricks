#!/bin/bash
set -e
rm -rf images/{packer,packer_cache}
rm -rf images/output-*/*.raw
rm -rf images/kernel/kheaders
find images/kernel \
    -maxdepth 1 \
    -regex "^images/kernel/linux-[0-9]*\.[0-9]*\.[0-9]*$" \
    -type d \
    -exec rm -rf {} \;
