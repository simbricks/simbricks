#!/bin/bash
set -e

mkdir -p sims/external/ns-3-new/
cd sims/external/ns-3
find build -name '*.o' -delete
cp -r \
  build/ \
  cosim-run.sh \
  cosim-dctcp-run.sh \
  ../ns-3-new/
cd ..
git submodule deinit -f ns-3
rm -rf ../../.git/modules/sims/external/ns-3
rm -rf ns-3
mv ns-3-new ns-3
touch ns-3/ready
