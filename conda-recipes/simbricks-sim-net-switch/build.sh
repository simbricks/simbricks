#!/bin/bash

make sims/net/switch/net_switch \
    SIMBRICKS_INC_DIR="${PREFIX}/lib/simbricks" \
    SWITCH_DEPS="${PREFIX}/lib/simbricks/libnicif.a \
               ${PREFIX}/lib/simbricks/libnetwork.a \
               ${PREFIX}/lib/simbricks/libbase.a"

make install-net-switch PREFIX=${PREFIX}
