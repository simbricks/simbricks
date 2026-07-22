#!/bin/bash

# Compile lib as normal
make -j${CPU_COUNT} dist/rdma/net_rdma
make -j${CPU_COUNT} dist/sockets/net_sockets

# Install using Conda's automated $PREFIX
make install-dist PREFIX=${PREFIX}
