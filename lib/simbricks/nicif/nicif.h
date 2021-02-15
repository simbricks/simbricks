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

int SimbricksNicIfInit(struct SimbricksNicIfParams *params,
                       struct SimbricksProtoPcieDevIntro *di);
void SimbricksNicIfCleanup(void);

int SimbricksNicIfSync(struct SimbricksNicIfParams *params, uint64_t timestamp);
void SimbricksNicIfAdvanceEpoch(struct SimbricksNicIfParams *params,
                                uint64_t timestamp);
uint64_t SimbricksNicIfAdvanceTime(struct SimbricksNicIfParams *params,
                                   uint64_t timestamp);
uint64_t SimbricksNicIfNextTimestamp(struct SimbricksNicIfParams *params);

volatile union SimbricksProtoPcieH2D *SimbricksNicIfH2DPoll(
    struct SimbricksNicIfParams *params, uint64_t timestamp);
void SimbricksNicIfH2DDone(volatile union SimbricksProtoPcieH2D *msg);
void SimbricksNicIfH2DNext(void);

volatile union SimbricksProtoPcieD2H *SimbricksNicIfD2HAlloc(
    struct SimbricksNicIfParams *params, uint64_t timestamp);

volatile union SimbricksProtoNetN2D *SimbricksNicIfN2DPoll(
    struct SimbricksNicIfParams *params, uint64_t timestamp);
void SimbricksNicIfN2DDone(volatile union SimbricksProtoNetN2D *msg);
void SimbricksNicIfN2DNext(void);

volatile union SimbricksProtoNetD2N *SimbricksNicIfD2NAlloc(
    struct SimbricksNicIfParams *params, uint64_t timestamp);

#endif  // SIMBRICKS_NICIF_NICIF_H_
