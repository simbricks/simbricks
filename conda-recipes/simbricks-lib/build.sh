#!/bin/bash

# Compile lib as normal
make -j${CPU_COUNT}

# Install using Conda's automated $PREFIX
make install-lib PREFIX=${PREFIX}