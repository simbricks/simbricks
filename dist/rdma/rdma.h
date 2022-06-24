/*
 * Copyright 2021 Max Planck Institute for Software Systems, and
 * National University of Singapore
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#ifndef DIST_RDMA_RDMA_H_
#define DIST_RDMA_RDMA_H_

#include <infiniband/verbs.h>

#include "dist/rdma/net_rdma.h"

int RdmaCommonInit(struct ibv_context *ctx);

int RdmaCMListen(struct sockaddr_in *addr);
int RdmaCMConnect(struct sockaddr_in *addr);
struct ibv_qp *RdmaCMCreateQP(struct ibv_pd *pd, struct ibv_qp_init_attr *attr);

int RdmaIBListen(struct sockaddr_in *addr);
int RdmaIBConnect(struct sockaddr_in *addr);
struct ibv_qp *RdmaIBCreateQP(struct ibv_pd *pd, struct ibv_qp_init_attr *attr);

#endif  // DIST_RDMA_RDMA_H_
