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

#include "lib/simbricks/nicif/nicif.h"

#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <simbricks/proto/base.h>

#include "lib/simbricks/nicif/internal.h"

#define D2H_ELEN (9024 + 64)
#define D2H_ENUM 1024

#define H2D_ELEN (9024 + 64)
#define H2D_ENUM 1024

#define D2N_ELEN (9024 + 64)
#define D2N_ENUM 8192

#define N2D_ELEN (9024 + 64)
#define N2D_ENUM 8192






static int accept_pci(struct SimbricksNicIf *nicif,
                      struct SimbricksProtoPcieDevIntro *di,
                      int pci_lfd,
                      int *sync_pci) {
  if ((nicif->pci_cfd = accept(pci_lfd, NULL, NULL)) < 0) {
    return -1;
  }
  close(pci_lfd);
  printf("pci connection accepted\n");

  di->d2h_offset = nicif->d2h_off;
  di->d2h_elen = D2H_ELEN;
  di->d2h_nentries = D2H_ENUM;

  di->h2d_offset = nicif->h2d_off;
  di->h2d_elen = H2D_ELEN;
  di->h2d_nentries = H2D_ENUM;

  if (*sync_pci)
    di->flags |= SIMBRICKS_PROTO_PCIE_FLAGS_DI_SYNC;
  else
    di->flags &= ~((uint64_t)SIMBRICKS_PROTO_PCIE_FLAGS_DI_SYNC);

  if (uxsocket_send(nicif->pci_cfd, di, sizeof(*di), nicif->shm_fd)) {
    return -1;
  }
  printf("pci intro sent\n");
  return 0;
}

static int accept_eth(struct SimbricksNicIf *nicif,
                      int eth_lfd,
                      int *sync_eth) {
  struct SimbricksProtoNetDevIntro di;

  if ((nicif->eth_cfd = accept(eth_lfd, NULL, NULL)) < 0) {
    return -1;
  }
  close(eth_lfd);
  printf("eth connection accepted\n");

  memset(&di, 0, sizeof(di));
  di.flags = 0;
  if (*sync_eth)
    di.flags |= SIMBRICKS_PROTO_NET_FLAGS_DI_SYNC;

  di.d2n_offset = nicif->d2n_off;
  di.d2n_elen = D2N_ELEN;
  di.d2n_nentries = D2N_ENUM;

  di.n2d_offset = nicif->n2d_off;
  di.n2d_elen = N2D_ELEN;
  di.n2d_nentries = N2D_ENUM;

  if (uxsocket_send(nicif->eth_cfd, &di, sizeof(di), nicif->shm_fd)) {
    return -1;
  }
  printf("eth intro sent\n");
  return 0;
}

static int accept_conns(struct SimbricksNicIf *nicif,
                        struct SimbricksProtoPcieDevIntro *di, int pci_lfd,
                        int *sync_pci, int eth_lfd, int *sync_eth) {
  struct pollfd pfds[2];
  int await_pci = pci_lfd != -1;
  int await_eth = eth_lfd != -1;
  int ret;

  while (await_pci || await_eth) {
    if (await_pci && await_eth) {
      /* we're waiting on both fds */
      pfds[0].fd = pci_lfd;
      pfds[1].fd = eth_lfd;
      pfds[0].events = pfds[1].events = POLLIN;
      pfds[0].revents = pfds[1].revents = 0;

      ret = poll(pfds, 2, -1);
      if (ret < 0) {
        perror("poll failed");
        return -1;
      }

      if (pfds[0].revents) {
        if (accept_pci(nicif, di, pci_lfd, sync_pci) != 0)
          return -1;
        await_pci = 0;
      }
      if (pfds[1].revents) {
        if (accept_eth(nicif, eth_lfd, sync_eth) != 0)
          return -1;
        await_eth = 0;
      }
    } else if (await_pci) {
      /* waiting just on pci */
      if (accept_pci(nicif, di, pci_lfd, sync_pci) != 0)
        return -1;
      await_pci = 0;
    } else {
      /* waiting just on ethernet */
      if (accept_eth(nicif, eth_lfd, sync_eth) != 0)
        return -1;
      await_eth = 0;
    }
  }

  return 0;
}

int SimbricksNicIfInit(struct SimbricksNicIf *nicif,
                       struct SimbricksNicIfParams *params,
                       struct SimbricksProtoPcieDevIntro *di) {
  int pci_lfd = -1, eth_lfd = -1;
  void *shmptr;
  size_t shm_size;

  /* initialize nicif struct */
  memset(nicif, 0, sizeof(*nicif));
  nicif->params = *params;
  nicif->pci_cfd = nicif->eth_cfd = -1;

  /* ready in memory queues */
  shm_size = (uint64_t)D2H_ELEN * D2H_ENUM + (uint64_t)H2D_ELEN * H2D_ENUM +
             (uint64_t)D2N_ELEN * D2N_ENUM + (uint64_t)N2D_ELEN * N2D_ENUM;
  if ((nicif->shm_fd = shm_create(params->shm_path, shm_size, &shmptr)) < 0) {
    return -1;
  }

  nicif->d2h_off = 0;
  nicif->h2d_off = nicif->d2h_off + (uint64_t)D2H_ELEN * D2H_ENUM;
  nicif->d2n_off = nicif->h2d_off + (uint64_t)H2D_ELEN * H2D_ENUM;
  nicif->n2d_off = nicif->d2n_off + (uint64_t)D2N_ELEN * D2N_ENUM;

  nicif->d2h_queue = (uint8_t *)shmptr + nicif->d2h_off;
  nicif->h2d_queue = (uint8_t *)shmptr + nicif->h2d_off;
  nicif->d2n_queue = (uint8_t *)shmptr + nicif->d2n_off;
  nicif->n2d_queue = (uint8_t *)shmptr + nicif->n2d_off;

  nicif->d2h_pos = nicif->h2d_pos = nicif->d2n_pos = nicif->n2d_pos = 0;

  /* get listening sockets ready */
  if (params->pci_socket_path != NULL) {
    if ((pci_lfd = uxsocket_init(params->pci_socket_path)) < 0) {
      return -1;
    }
  }
  if (params->eth_socket_path != NULL) {
    if ((eth_lfd = uxsocket_init(params->eth_socket_path)) < 0) {
      return -1;
    }
  }

  /* accept connection fds */
  if (accept_conns(nicif, di, pci_lfd, &params->sync_pci, eth_lfd,
                   &params->sync_eth) != 0) {
    return -1;
  }

  /* receive introductions from other end */
  if (params->pci_socket_path != NULL) {
    struct SimbricksProtoPcieHostIntro hi;
    if (recv(nicif->pci_cfd, &hi, sizeof(hi), 0) != sizeof(hi)) {
      return -1;
    }
    if ((hi.flags & SIMBRICKS_PROTO_PCIE_FLAGS_HI_SYNC) == 0)
      params->sync_pci = 0;
    printf("pci host info received\n");
  }
  if (params->eth_socket_path != NULL) {
    struct SimbricksProtoNetNetIntro ni;
    if (recv(nicif->eth_cfd, &ni, sizeof(ni), 0) != sizeof(ni)) {
      return -1;
    }
    if ((ni.flags & SIMBRICKS_PROTO_NET_FLAGS_NI_SYNC) == 0)
      params->sync_eth = 0;
    printf("eth net info received\n");
  }

  nicif->params.sync_pci = params->sync_pci;
  nicif->params.sync_eth = params->sync_eth;
  return 0;
}

void SimbricksNicIfCleanup(struct SimbricksNicIf *nicif) {
  close(nicif->pci_cfd);
  close(nicif->eth_cfd);
}

/******************************************************************************/
/* Sync */

int SimbricksNicIfSync(struct SimbricksNicIf *nicif,
                       uint64_t timestamp) {
  int ret = 0;
  struct SimbricksNicIfParams *params = &nicif->params;
  volatile union SimbricksProtoPcieD2H *d2h;
  volatile union SimbricksProtoNetD2N *d2n;

  /* sync PCI if necessary */
  if (params->sync_pci) {
    int sync;
    switch (params->sync_mode) {
      case SIMBRICKS_PROTO_SYNC_SIMBRICKS:
        sync = nicif->pci_last_tx_time == 0 ||
               timestamp - nicif->pci_last_tx_time >= params->sync_delay;
        break;
      case SIMBRICKS_PROTO_SYNC_BARRIER:
        sync = nicif->current_epoch == 0 ||
               timestamp - nicif->current_epoch >= params->sync_delay;
        break;
      default:
        fprintf(stderr, "unsupported sync mode=%u\n", params->sync_mode);
        return ret;
    }

    if (sync) {
      d2h = SimbricksNicIfD2HAlloc(nicif, timestamp);
      if (d2h == NULL) {
        ret = -1;
      } else {
        d2h->sync.own_type = SIMBRICKS_PROTO_PCIE_D2H_MSG_SYNC |
                             SIMBRICKS_PROTO_PCIE_D2H_OWN_HOST;
      }
    }
  }

  /* sync Ethernet if necessary */
  if (params->sync_eth) {
    int sync;
    switch (params->sync_mode) {
      case SIMBRICKS_PROTO_SYNC_SIMBRICKS:
        sync = nicif->eth_last_tx_time == 0 ||
               timestamp - nicif->eth_last_tx_time >= params->sync_delay;
        break;
      case SIMBRICKS_PROTO_SYNC_BARRIER:
        sync = nicif->current_epoch == 0 ||
               timestamp - nicif->current_epoch >= params->sync_delay;
        break;
      default:
        fprintf(stderr, "unsupported sync mode=%u\n", params->sync_mode);
        return ret;
    }

    if (sync) {
      d2n = SimbricksNicIfD2NAlloc(nicif, timestamp);
      if (d2n == NULL) {
        ret = -1;
      } else {
        d2n->sync.own_type =
            SIMBRICKS_PROTO_NET_D2N_MSG_SYNC | SIMBRICKS_PROTO_NET_D2N_OWN_NET;
      }
    }
  }

  return ret;
}

void SimbricksNicIfAdvanceEpoch(struct SimbricksNicIf *nicif,
                                uint64_t timestamp) {
  struct SimbricksNicIfParams *params = &nicif->params;
  if (params->sync_mode == SIMBRICKS_PROTO_SYNC_BARRIER) {
    if ((params->sync_pci || params->sync_eth) &&
        timestamp - nicif->current_epoch >= params->sync_delay) {
      nicif->current_epoch = timestamp;
    }
  }
}

uint64_t SimbricksNicIfAdvanceTime(struct SimbricksNicIf *nicif,
                                   uint64_t timestamp) {
  struct SimbricksNicIfParams *params = &nicif->params;
  switch (params->sync_mode) {
    case SIMBRICKS_PROTO_SYNC_SIMBRICKS:
      return timestamp;
    case SIMBRICKS_PROTO_SYNC_BARRIER:
      return timestamp < nicif->current_epoch + params->sync_delay
                 ? timestamp
                 : nicif->current_epoch + params->sync_delay;
    default:
      fprintf(stderr, "unsupported sync mode=%u\n", params->sync_mode);
      return timestamp;
  }
}

uint64_t SimbricksNicIfNextTimestamp(struct SimbricksNicIf *nicif) {
  struct SimbricksNicIfParams *params = &nicif->params;
  if (params->sync_pci && params->sync_eth) {
    return (nicif->pci_last_rx_time <= nicif->eth_last_rx_time ?
              nicif->pci_last_rx_time :
              nicif->eth_last_rx_time);
  } else if (params->sync_pci) {
    return nicif->pci_last_rx_time;
  } else if (params->sync_eth) {
    return nicif->eth_last_rx_time;
  } else {
    return 0;
  }
}

/******************************************************************************/
/* PCI */

volatile union SimbricksProtoPcieH2D *SimbricksNicIfH2DPoll(
    struct SimbricksNicIf *nicif, uint64_t timestamp) {
  volatile union SimbricksProtoPcieH2D *msg =
      (volatile union SimbricksProtoPcieH2D *)
      (nicif->h2d_queue + nicif->h2d_pos * H2D_ELEN);

  /* message not ready */
  if ((msg->dummy.own_type & SIMBRICKS_PROTO_PCIE_H2D_OWN_MASK) !=
      SIMBRICKS_PROTO_PCIE_H2D_OWN_DEV)
    return NULL;

  /* if in sync mode, wait till message is ready */
  nicif->pci_last_rx_time = msg->dummy.timestamp;
  if (nicif->params.sync_pci && nicif->pci_last_rx_time > timestamp)
    return NULL;

  return msg;
}

void SimbricksNicIfH2DDone(struct SimbricksNicIf *nicif,
                           volatile union SimbricksProtoPcieH2D *msg) {
  msg->dummy.own_type =
      (msg->dummy.own_type & SIMBRICKS_PROTO_PCIE_H2D_MSG_MASK) |
      SIMBRICKS_PROTO_PCIE_H2D_OWN_HOST;
}

void SimbricksNicIfH2DNext(struct SimbricksNicIf *nicif) {
  nicif->h2d_pos = (nicif->h2d_pos + 1) % H2D_ENUM;
}

volatile union SimbricksProtoPcieD2H *SimbricksNicIfD2HAlloc(
    struct SimbricksNicIf *nicif, uint64_t timestamp) {
  volatile union SimbricksProtoPcieD2H *msg =
      (volatile union SimbricksProtoPcieD2H *)
      (nicif->d2h_queue + nicif->d2h_pos * D2H_ELEN);

  if ((msg->dummy.own_type & SIMBRICKS_PROTO_PCIE_D2H_OWN_MASK) !=
      SIMBRICKS_PROTO_PCIE_D2H_OWN_DEV) {
    return NULL;
  }

  msg->dummy.timestamp = timestamp + nicif->params.pci_latency;
  nicif->pci_last_tx_time = timestamp;

  nicif->d2h_pos = (nicif->d2h_pos + 1) % D2H_ENUM;
  return msg;
}

/******************************************************************************/
/* Ethernet */

volatile union SimbricksProtoNetN2D *SimbricksNicIfN2DPoll(
    struct SimbricksNicIf *nicif, uint64_t timestamp) {
  volatile union SimbricksProtoNetN2D *msg =
      (volatile union SimbricksProtoNetN2D *)
      (nicif->n2d_queue + nicif->n2d_pos * N2D_ELEN);

  /* message not ready */
  if ((msg->dummy.own_type & SIMBRICKS_PROTO_NET_N2D_OWN_MASK) !=
      SIMBRICKS_PROTO_NET_N2D_OWN_DEV)
    return NULL;

  /* if in sync mode, wait till message is ready */
  nicif->eth_last_rx_time = msg->dummy.timestamp;
  if (nicif->params.sync_eth && nicif->eth_last_rx_time > timestamp)
    return NULL;

  return msg;
}

void SimbricksNicIfN2DDone(struct SimbricksNicIf *nicif,
                           volatile union SimbricksProtoNetN2D *msg) {
  msg->dummy.own_type =
      (msg->dummy.own_type & SIMBRICKS_PROTO_NET_N2D_MSG_MASK) |
      SIMBRICKS_PROTO_NET_N2D_OWN_NET;
}

void SimbricksNicIfN2DNext(struct SimbricksNicIf *nicif) {
  nicif->n2d_pos = (nicif->n2d_pos + 1) % N2D_ENUM;
}

volatile union SimbricksProtoNetD2N *SimbricksNicIfD2NAlloc(
    struct SimbricksNicIf *nicif, uint64_t timestamp) {
  volatile union SimbricksProtoNetD2N *msg =
      (volatile union SimbricksProtoNetD2N *)
      (nicif->d2n_queue + nicif->d2n_pos * D2N_ELEN);

  if ((msg->dummy.own_type & SIMBRICKS_PROTO_NET_D2N_OWN_MASK) !=
      SIMBRICKS_PROTO_NET_D2N_OWN_DEV) {
    return NULL;
  }

  msg->dummy.timestamp = timestamp + nicif->params.eth_latency;
  nicif->eth_last_tx_time = timestamp;

  nicif->d2n_pos = (nicif->d2n_pos + 1) % D2N_ENUM;
  return msg;
}
