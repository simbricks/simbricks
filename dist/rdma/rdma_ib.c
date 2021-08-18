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

#include "dist/rdma/rdma.h"
#include "dist/rdma/net_rdma.h"

#include <rdma/rdma_cma.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>


struct RdmaIBInitMsg {
  union ibv_gid gid;
  uint32_t lid;
  uint32_t qpn;
  uint32_t psn;
} __attribute__((packed));

static int sock_fd;
static struct ibv_context *ib_ctx;
static struct ibv_qp *ib_qp;
static uint32_t psn_local;

static int SockListen(struct sockaddr_in *addr) {
  int lfd;
  if ((lfd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0) {
    perror("RdmaIBListen: socket failed");
    return 1;
  }

  int flag;
  flag = 1;
  if (setsockopt(lfd, SOL_SOCKET, SO_REUSEPORT, &flag, sizeof(flag))) {
    perror("RdmaIBListen: setsockopt reuseport faild");
    return 1;
  }

  if (bind(lfd, (struct sockaddr *) addr, sizeof(*addr))) {
    perror("RdmaIBListen: bind failed");
    return 1;
  }

  if (listen(lfd, 1)) {
    perror("RdmaIBListen: listen");
    return 1;
  }

  if ((sock_fd = accept(lfd, NULL, 0)) < 0) {
    perror("RdmaIBListen: accept failed");
    return 1;
  }

  return 0;
}

static int SockConnect(struct sockaddr_in *addr) {
  if ((sock_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0) {
    perror("RdmaIBConnect: socket failed");
    return 1;
  }

  if (connect(sock_fd, (struct sockaddr *) addr, sizeof(*addr))) {
    perror("RdmaIBConnect: connect failed");
  }
  return 0;
}

static int CommonInit() {
  struct ibv_device **dev_list;
  struct ibv_device *dev;

  if (!(dev_list = ibv_get_device_list(NULL))) {
    perror("CommonInit: ibv_get_device_list failed");
    return 1;
  }
  if (ib_devname) {
    // if a name was specified, find the device with this name
    size_t i;
    dev = NULL;
    for (i = 0; dev_list[i]; i++) {
      if (!strcmp(ibv_get_device_name(dev_list[i]), ib_devname)) {
        dev = dev_list[i];
        break;
      }
    }
  } else {
    // otherwise we pick the first one
    dev = dev_list[0];
  }
  if (!dev) {
    fprintf(stderr, "CommonInit: IB device not found\n");
    return 1;
  }

  if (!(ib_ctx = ibv_open_device(dev))) {
    perror("CommonInit: ibv_open_device failed");
    return 1;
  }

  ibv_free_device_list(dev_list);

  struct ibv_port_attr port_attr;
  if (ibv_query_port(ib_ctx, ib_port, &port_attr)) {
    perror("CommonInit: ibv_query_port failed");
    return 1;
  }

  srand48(getpid() * time(NULL));
  psn_local = lrand48() & 0xffffff;

  if (RdmaCommonInit(ib_ctx))
    return 1;

  if (!ib_qp) {
    fprintf(stderr, "CommonInit: no queue pair created after RdmaCommonInit\n");
    abort();
  }

  // here we should have a queue pair in init state, so we are ready for the
  // handshake.
  struct RdmaIBInitMsg out_msg;
  if (ib_sgid_idx >= 0) {
    if (ibv_query_gid(ib_ctx, ib_port, ib_sgid_idx, &out_msg.gid)) {
      perror("CommonInit: ibv_query_gid failed");
    }
  } else {
    memset(&out_msg.gid, 0, sizeof(out_msg.gid));
  }
  out_msg.lid = port_attr.lid;
  out_msg.qpn = ib_qp->qp_num;
  out_msg.psn = psn_local;


  if (write(sock_fd, &out_msg, sizeof(out_msg)) != sizeof(out_msg)) {
    perror("CommonInit: write failed");
  }

  struct RdmaIBInitMsg in_msg;
  if (read(sock_fd, &in_msg, sizeof(in_msg)) != sizeof(in_msg)) {
    perror("CommonInit: read failed");
  }

#ifdef RDMA_DEBUG
  fprintf(stderr, "out: lid=%x qpn=%x psn=%x iid=%lx\n", out_msg.lid,
          out_msg.qpn, out_msg.psn, out_msg.gid.global.interface_id);
  fprintf(stderr, "in: lid=%x qpn=%x psn=%x iid=%lx\n", in_msg.lid,
          in_msg.qpn, in_msg.psn, in_msg.gid.global.interface_id);
#endif

  // change queue pair to "ready to receive"
  struct ibv_qp_attr attr;
  memset(&attr, 0, sizeof(attr));
  attr.qp_state = IBV_QPS_RTR;
  attr.path_mtu = port_attr.active_mtu;
  attr.dest_qp_num = in_msg.qpn;
  attr.rq_psn = in_msg.psn;
  attr.max_dest_rd_atomic = 1;
  attr.min_rnr_timer = 12;
  attr.ah_attr.is_global = 0;
  attr.ah_attr.dlid = in_msg.lid;
  attr.ah_attr.sl = 0;
  attr.ah_attr.src_path_bits = 0;
  attr.ah_attr.port_num = ib_port;

  if (in_msg.gid.global.interface_id) {
    attr.ah_attr.is_global = 1;
    attr.ah_attr.grh.hop_limit = 1;
    attr.ah_attr.grh.dgid = in_msg.gid;
    attr.ah_attr.grh.sgid_index = ib_sgid_idx;
  }
  if (ibv_modify_qp(ib_qp, &attr,
                    IBV_QP_STATE |
                      IBV_QP_AV |
                      IBV_QP_PATH_MTU |
                      IBV_QP_DEST_QPN |
                      IBV_QP_RQ_PSN |
                      IBV_QP_MAX_DEST_RD_ATOMIC |
                      IBV_QP_MIN_RNR_TIMER)) {
    perror("CommonInit: Failed to modify QP to RTR");
    return 1;
  }

  // change queue pair to "ready to send"
  attr.qp_state = IBV_QPS_RTS;
  attr.timeout = 14;
  attr.retry_cnt = 7;
  attr.rnr_retry = 7;
  attr.sq_psn = psn_local;
  attr.max_rd_atomic = 1;
  if (ibv_modify_qp(ib_qp, &attr,
                    IBV_QP_STATE |
                      IBV_QP_TIMEOUT |
                      IBV_QP_RETRY_CNT |
                      IBV_QP_RNR_RETRY |
                      IBV_QP_SQ_PSN |
                      IBV_QP_MAX_QP_RD_ATOMIC)) {
    perror("CommonInit: Failed to modify QP to RTS");
    return 1;
  }

  return 0;
}

int RdmaIBListen(struct sockaddr_in *addr) {
  if (SockListen(addr))
    return 1;

  return CommonInit();
}

int RdmaIBConnect(struct sockaddr_in *addr) {
  if (SockConnect(addr))
    return 1;

  return CommonInit();
}

struct ibv_qp *RdmaIBCreateQP(struct ibv_pd *pd,
                              struct ibv_qp_init_attr *attr) {
  // create queue pair in reset state
  if (!(ib_qp = ibv_create_qp(pd, attr))) {
    perror("RdmaIBCreateQP: ibv_create_qp failed");
    return NULL;
  }

  // transition queue pair from reset to init state
  struct ibv_qp_attr attr_init = {
    .qp_state = IBV_QPS_INIT,
    .pkey_index = 0,
    .port_num = ib_port,
    .qp_access_flags = 0
  };
  if (ibv_modify_qp(ib_qp, &attr_init,
                    IBV_QP_STATE |
                      IBV_QP_PKEY_INDEX |
                      IBV_QP_PORT |
                      IBV_QP_ACCESS_FLAGS)) {
    perror("RdmaIBCreateQP: ibv_modify_qp failed (reset -> init)");
    ibv_destroy_qp(ib_qp);
    return NULL;
  }

  /* Here the queue pair is not connected yet, but it is ready for recv
     operations to be posted. The rest of the initalization we do after
     RDMACommonInit returns. */
  return ib_qp;
}
