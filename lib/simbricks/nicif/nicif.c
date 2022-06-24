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
#include <string.h>

int SimbricksNicIfInit(struct SimbricksNicIf *nicif, const char *shm_path,
                       struct SimbricksBaseIfParams *netParams,
                       struct SimbricksBaseIfParams *pcieParams,
                       struct SimbricksProtoPcieDevIntro *di) {
  struct SimbricksBaseIf *netif = &nicif->net.base;
  struct SimbricksBaseIf *pcieif = &nicif->pcie.base;

  // first allocate pool
  size_t shm_size = 0;
  if (netParams) {
    shm_size += netParams->in_num_entries * netParams->in_entries_size;
    shm_size += netParams->out_num_entries * netParams->out_entries_size;
  }
  if (pcieParams) {
    shm_size += pcieParams->in_num_entries * pcieParams->in_entries_size;
    shm_size += pcieParams->out_num_entries * pcieParams->out_entries_size;
  }
  if (SimbricksBaseIfSHMPoolCreate(&nicif->pool, shm_path, shm_size)) {
    perror("SimbricksNicIfInit: SimbricksBaseIfSHMPoolCreate failed");
    return -1;
  }

  struct SimBricksBaseIfEstablishData ests[2];
  struct SimbricksProtoNetIntro net_intro;
  struct SimbricksProtoPcieHostIntro pcie_h_intro;
  unsigned n_bifs = 0;
  if (netParams) {
    if (SimbricksBaseIfInit(netif, netParams)) {
      perror("SimbricksNicIfInit: SimbricksBaseIfInit net failed");
      return -1;
    }

    if (SimbricksBaseIfListen(netif, &nicif->pool)) {
      perror("SimbricksNicIfInit: SimbricksBaseIfListen net failed");
      return -1;
    }

    memset(&net_intro, 0, sizeof(net_intro));
    ests[n_bifs].base_if = netif;
    ests[n_bifs].tx_intro = &net_intro;
    ests[n_bifs].tx_intro_len = sizeof(net_intro);
    ests[n_bifs].rx_intro = &net_intro;
    ests[n_bifs].rx_intro_len = sizeof(net_intro);
    n_bifs++;
  }

  if (pcieParams) {
    if (SimbricksBaseIfInit(pcieif, pcieParams)) {
      perror("SimbricksNicIfInit: SimbricksBaseIfInit pcie failed");
      return -1;
    }

    if (SimbricksBaseIfListen(pcieif, &nicif->pool)) {
      perror("SimbricksNicIfInit: SimbricksBaseIfListen pcie failed");
      return -1;
    }
    ests[n_bifs].base_if = pcieif;
    ests[n_bifs].tx_intro = di;
    ests[n_bifs].tx_intro_len = sizeof(*di);
    ests[n_bifs].rx_intro = &pcie_h_intro;
    ests[n_bifs].rx_intro_len = sizeof(pcie_h_intro);
    n_bifs++;
  }

  return SimBricksBaseIfEstablish(ests, n_bifs);
}

int SimbricksNicIfCleanup(struct SimbricksNicIf *nicif) {
  SimbricksBaseIfClose(&nicif->pcie.base);
  SimbricksBaseIfClose(&nicif->net.base);
  /* TODO: unlink? */
  return -1;
}
