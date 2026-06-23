#!/bin/bash

make sims/nic/i40e_bm/i40e_bm \
    SIMBRICKS_INC_DIR="${PREFIX}/lib/simbricks" \
    I40E_DEPS="${PREFIX}/lib/simbricks/libnicbm.a \
               ${PREFIX}/lib/simbricks/libnicif.a \
               ${PREFIX}/lib/simbricks/libnetwork.a \
               ${PREFIX}/lib/simbricks/libpcie.a \
               ${PREFIX}/lib/simbricks/libbase.a"

make install-i40e PREFIX=${PREFIX}
