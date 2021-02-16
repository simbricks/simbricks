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

#ifndef SIMBRICKS_NETIF_NETIF_H_
#define SIMBRICKS_NETIF_NETIF_H_

#include <stddef.h>
#include <stdint.h>

#include <simbricks/proto/network.h>

struct SimbricksNetIf {
  uint8_t *d2n_queue;
  size_t d2n_pos;
  size_t d2n_elen;
  size_t d2n_enum;
  uint64_t d2n_timestamp;

  uint8_t *n2d_queue;
  size_t n2d_pos;
  size_t n2d_elen;
  size_t n2d_enum;
  uint64_t n2d_timestamp;

  int sync;
};

int SimbricksNetIfInit(struct SimbricksNetIf *nsif, const char *eth_socket_path,
                       int *sync_eth);
void SimbricksNetIfCleanup(struct SimbricksNetIf *nsif);

volatile union SimbricksProtoNetD2N *SimbricksNetIfD2NPoll(
    struct SimbricksNetIf *nsif, uint64_t timestamp);
void SimbricksNetIfD2NDone(struct SimbricksNetIf *nsif,
                           volatile union SimbricksProtoNetD2N *msg);
static inline uint64_t SimbricksNetIfD2NTimestamp(struct SimbricksNetIf *nsif) {
  return nsif->d2n_timestamp;
}

volatile union SimbricksProtoNetN2D *SimbricksNetIfN2DAlloc(
    struct SimbricksNetIf *nsif, uint64_t timestamp, uint64_t latency);
int SimbricksNetIfN2DSync(struct SimbricksNetIf *nsif, uint64_t timestamp,
                          uint64_t latency, uint64_t sync_delay, int sync_mode);
void SimbricksNetIfAdvanceEpoch(uint64_t timestamp, uint64_t sync_delay,
                                int sync_mode);
uint64_t SimbricksNetIfAdvanceTime(uint64_t timestamp, uint64_t sync_delay,
                                   int sync_mode);

#endif  // SIMBRICKS_NETIF_NETIF_H_
