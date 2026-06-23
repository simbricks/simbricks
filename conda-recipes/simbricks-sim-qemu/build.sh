#!/bin/bash

unset CFLAGS
unset CXXFLAGS
unset LDFLAGS
unset CPP
unset AS
unset AR
unset LD
unset NM

# Trigger existing Makefile target, overriding the include/lib paths
make sims/external/qemu/ready \
    SIMBRICKS_INC_DIR=${PREFIX}/include \
    SIMBRICKS_LIB_DIR=${PREFIX}/lib/simbricks

# Install the binary into Conda's bin path so it is globally available in the environment
make qemu-install
