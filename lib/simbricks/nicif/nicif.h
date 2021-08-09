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

#ifndef SIMBRICKS_NICIF_NICIF_H_
#define SIMBRICKS_NICIF_NICIF_H_

#include <stddef.h>
#include <stdint.h>

#include <simbricks/proto/network.h>
#include <simbricks/proto/pcie.h>

struct SimbricksNicIfParams {
  const char *pci_socket_path;
  const char *eth_socket_path;
  const char *shm_path;

  uint64_t pci_latency;
  uint64_t eth_latency;
  uint64_t sync_delay;

  int sync_pci;
  int sync_eth;
  int sync_mode;
};

struct SimbricksNicIf {
  uint8_t *d2h_queue;
  size_t d2h_pos;
  size_t d2h_off; /* offset in shm region */

  uint8_t *h2d_queue;
  size_t h2d_pos;
  size_t h2d_off; /* offset in shm region */

  uint8_t *d2n_queue;
  size_t d2n_pos;
  size_t d2n_off; /* offset in shm region */

  uint8_t *n2d_queue;
  size_t n2d_pos;
  size_t n2d_off; /* offset in shm region */

  uint64_t pci_last_rx_time;
  uint64_t pci_last_tx_time;
  uint64_t eth_last_rx_time;
  uint64_t eth_last_tx_time;
  uint64_t current_epoch;

  struct SimbricksNicIfParams params;

  int shm_fd;
  int pci_cfd;
  int eth_cfd;
};

int SimbricksNicIfInit(struct SimbricksNicIf *nicif,
                       struct SimbricksNicIfParams *params,
                       struct SimbricksProtoPcieDevIntro *di);
void SimbricksNicIfCleanup(struct SimbricksNicIf *nicif);

int SimbricksNicIfSync(struct SimbricksNicIf *nicif,
                       uint64_t timestamp);
void SimbricksNicIfAdvanceEpoch(struct SimbricksNicIf *nicif,
                                uint64_t timestamp);
uint64_t SimbricksNicIfAdvanceTime(struct SimbricksNicIf *nicif,
                                   uint64_t timestamp);
uint64_t SimbricksNicIfNextTimestamp(struct SimbricksNicIf *nicif);

volatile union SimbricksProtoPcieH2D *SimbricksNicIfH2DPoll(
    struct SimbricksNicIf *nicif, uint64_t timestamp);
void SimbricksNicIfH2DDone(struct SimbricksNicIf *nicif,
                           volatile union SimbricksProtoPcieH2D *msg);
void SimbricksNicIfH2DNext(struct SimbricksNicIf *nicif);

volatile union SimbricksProtoPcieD2H *SimbricksNicIfD2HAlloc(
    struct SimbricksNicIf *nicif, uint64_t timestamp);

volatile union SimbricksProtoNetN2D *SimbricksNicIfN2DPoll(
    struct SimbricksNicIf *nicif, uint64_t timestamp);
void SimbricksNicIfN2DDone(struct SimbricksNicIf *nicif,
                           volatile union SimbricksProtoNetN2D *msg);
void SimbricksNicIfN2DNext(struct SimbricksNicIf *nicif);

volatile union SimbricksProtoNetD2N *SimbricksNicIfD2NAlloc(
    struct SimbricksNicIf *nicif, uint64_t timestamp);

#endif  // SIMBRICKS_NICIF_NICIF_H_
