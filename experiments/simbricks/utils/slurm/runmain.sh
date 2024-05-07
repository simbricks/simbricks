#!/bin/bash

bash prepcontainer.sh rootfs.tar /tmp/simbrickscontainer
mkdir -p ./out

python3 modify_oci.py --json=/tmp/simbrickscontainer/config.json \
	--cmd="/usr/bin/simbricks-run --verbose --force --hosts /hosts.json --outdir=/out $*" \
	--mount `pwd`:/slurm `pwd`/hosts.json:/hosts.json `pwd`/out:/out 

cd /tmp/simbrickscontainer
runc --root root run mycontainerid
