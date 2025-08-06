#!/bin/bash
set -e

sudo ln -s `pwd` /simbricks

cd /simbricks

python3 -m venv venv
source venv/bin/activate

pip3 install -r requirements.txt
pip3 install -e symphony/orchestration
pip3 install -e symphony/runtime
pip3 install -e symphony/local
pip3 install -e symphony/utils
pip3 install -e symphony/client
pip3 install -e symphony/schemas/

make -j`nproc`
make -j`nproc` sims/external/qemu/ready
# make -j`nproc` build-images
make -j`nproc` images/output-enso/enso
