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

#include <rdma/rdma_cma.h>
#include <stdio.h>
#include <stdlib.h>

#include "dist/rdma/net_rdma.h"
#include "dist/rdma/rdma.h"

static struct rdma_event_channel *cm_channel;
static struct rdma_conn_param conn_param = {};
static struct rdma_cm_id *cm_id;

int RdmaCMListen(struct sockaddr_in *addr) {
  if (!(cm_channel = rdma_create_event_channel())) {
    perror("RdmaListen: rdma_create_event_channel failed");
    return 1;
  }

  struct rdma_cm_id *listen_id;
  if (rdma_create_id(cm_channel, &listen_id, NULL, RDMA_PS_TCP)) {
    perror("RdmaListen: rdma_create_id failed");
    return 1;
  }

  if (rdma_bind_addr(listen_id, (struct sockaddr *)addr)) {
    perror("RdmaListen: rdma_bind_addr failed");
    return 1;
  }

  if (rdma_listen(listen_id, 1)) {
    perror("RdmaListen: rdma_listen failed");
    return 1;
  }

#ifdef RDMA_DEBUG
  fprintf(stderr, "RdmaListen: listen done\n");
#endif
  struct rdma_cm_event *event;
  if (rdma_get_cm_event(cm_channel, &event)) {
    perror("RdmaListen: rdma_get_cm_event failed");
    return 1;
  }
  if (event->event != RDMA_CM_EVENT_CONNECT_REQUEST) {
    fprintf(stderr, "RdmaListen: unexpected event (%u)\n", event->event);
    return 1;
  }
  cm_id = event->id;
  rdma_ack_cm_event(event);

#ifdef RDMA_DEBUG
  fprintf(stderr, "RdmaListen: got conn request\n");
#endif

  if (RdmaCommonInit(cm_id->verbs))
    return 1;

  conn_param.responder_resources = 1;
  if (rdma_accept(cm_id, &conn_param)) {
    perror("RdmaListen: rdma_accept failed");
    return 1;
  }

#ifdef RDMA_DEBUG
  fprintf(stderr, "RdmaListen: accept done\n");
#endif

  if (rdma_get_cm_event(cm_channel, &event)) {
    perror("RdmaListen: rdma_get_cm_event failed");
    return 1;
  }
  if (event->event != RDMA_CM_EVENT_ESTABLISHED) {
    fprintf(stderr, "RdmaListen: unexpected event (%u)\n", event->event);
    return 1;
  }
  rdma_ack_cm_event(event);

#ifdef RDMA_DEBUG
  fprintf(stderr, "RdmaListen: conn established\n");
#endif

  return 0;
}

int RdmaCMConnect(struct sockaddr_in *addr) {
  if (!(cm_channel = rdma_create_event_channel())) {
    perror("RdmaConnect: rdma_create_event_channel failed");
    return 1;
  }

  if (rdma_create_id(cm_channel, &cm_id, NULL, RDMA_PS_TCP)) {
    perror("RdmaConnect: rdma_create_id failed");
    return 1;
  }

  if (rdma_resolve_addr(cm_id, NULL, (struct sockaddr *)addr, 5000)) {
    perror("RdmaConnect: rdma_resolve_addr failed");
    return 1;
  }
  struct rdma_cm_event *event;
  if (rdma_get_cm_event(cm_channel, &event)) {
    perror("RdmaConnect: rdma_get_cm_event failed (addr)");
    return 1;
  }
  if (event->event != RDMA_CM_EVENT_ADDR_RESOLVED) {
    fprintf(stderr, "RdmaConnect: unexpected event (%u instead of %u)\n",
            event->event, RDMA_CM_EVENT_ADDR_RESOLVED);
    return 1;
  }
  rdma_ack_cm_event(event);

#ifdef RDMA_DEBUG
  fprintf(stderr, "RdmaConnect: address resolved\n");
#endif

  if (rdma_resolve_route(cm_id, 5000)) {
    perror("RdmaConnect: rdma_resolve_route failed");
    return 1;
  }
  if (rdma_get_cm_event(cm_channel, &event)) {
    perror("RdmaConnect: rdma_get_cm_event failed (route)");
    return 1;
  }
  if (event->event != RDMA_CM_EVENT_ROUTE_RESOLVED) {
    fprintf(stderr, "RdmaConnect: unexpected event (%u instead of %u)\n",
            event->event, RDMA_CM_EVENT_ROUTE_RESOLVED);
    return 1;
  }
  rdma_ack_cm_event(event);

#ifdef RDMA_DEBUG
  fprintf(stderr, "RdmaConnect: route resolved\n");
#endif

  if (RdmaCommonInit(cm_id->verbs))
    return 1;

  conn_param.initiator_depth = 1;
  conn_param.retry_count = 7;
  if (rdma_connect(cm_id, &conn_param)) {
    perror("RdmaConnect: rdma_connect failed");
    return 1;
  }

#ifdef RDMA_DEBUG
  fprintf(stderr, "RdmaConnect: connect issued\n");
#endif

  if (rdma_get_cm_event(cm_channel, &event)) {
    perror("RdmaConnect: rdma_get_cm_event failed (connect)");
    return 1;
  }
  if (event->event != RDMA_CM_EVENT_ESTABLISHED) {
    fprintf(stderr, "RdmaConnect: unexpected event (%u)\n", event->event);
    return 1;
  }
  rdma_ack_cm_event(event);

  return 0;
}

struct ibv_qp *RdmaCMCreateQP(struct ibv_pd *pd,
                              struct ibv_qp_init_attr *attr) {
  if (rdma_create_qp(cm_id, pd, attr)) {
    perror("RdmaCommonInit: rdma_create_qp failed");
    return NULL;
  }
  return cm_id->qp;
}
