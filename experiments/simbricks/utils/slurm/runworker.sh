#!/bin/bash

bash prepcontainer.sh rootfs.tar /tmp/simbrickscontainer

python3 modify_oci.py --json=/tmp/simbrickscontainer/config.json \
	--cmd="/usr/sbin/sshd -e -D -p 2222"

echo Running container
cd /tmp/simbrickscontainer
runc --root root run mycontainerid
