#!/bin/bash
set -e

mkdir -p sims/external/gem5-new/
cd sims/external/gem5
cp -r --parents \
  build/X86/gem5.fast \
  configs \
  ../gem5-new/
#`find build -name \*.py` \
cd ..
test -f .git && git submodule deinit -f gem5
rm -rf ../../.git/modules/sims/external/gem5
rm -rf gem5
mv gem5-new gem5
touch gem5/ready
