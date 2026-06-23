#!/bin/bash

# Compile lib as normal
make -j${CPU_COUNT} lib/simbricks/base/libbase.a
make -j${CPU_COUNT} lib/simbricks/mem/libmem.a
make -j${CPU_COUNT} lib/simbricks/network/libnetwork.a
make -j${CPU_COUNT} lib/simbricks/nicbm/libnicbm.a
make -j${CPU_COUNT} lib/simbricks/nicif/libnicif.a
make -j${CPU_COUNT} lib/simbricks/parser/libparser.a
make -j${CPU_COUNT} lib/simbricks/pcie/libpcie.a
make -j${CPU_COUNT} lib/libsimbricks.a

# Install using Conda's automated $PREFIX
make install-lib PREFIX=${PREFIX}