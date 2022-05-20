#!/bin/bash
set -e
rm -rf images/{packer,packer_cache}
rm -rf images/output-*/*.raw
rm -rf images/kernel/{kheaders,linux-5.4.46}
