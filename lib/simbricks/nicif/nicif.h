/*
 * Copyright 2022 Max Planck Institute for Software Systems, and
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

#include <simbricks/network/if.h>
#include <simbricks/pcie/if.h>

struct SimbricksNicIf {
  struct SimbricksBaseIfSHMPool pool;
  struct SimbricksNetIf net;
  struct SimbricksPcieIf pcie;
};

int SimbricksNicIfInit(struct SimbricksNicIf *nicif, const char *shmPath,
                       struct SimbricksBaseIfParams *netParams,
                       struct SimbricksBaseIfParams *pcieParams,
                       struct SimbricksProtoPcieDevIntro *di);

int SimbricksNicIfCleanup(struct SimbricksNicIf *nicif);

static inline int SimbricksNicIfSync(struct SimbricksNicIf *nicif,
                                     uint64_t cur_ts) {
  return ((SimbricksNetIfOutSync(&nicif->net, cur_ts) == 0 &&
           SimbricksPcieIfD2HOutSync(&nicif->pcie, cur_ts) == 0)
              ? 0
              : -1);
}

static inline uint64_t SimbricksNicIfNextTimestamp(
    struct SimbricksNicIf *nicif) {
  uint64_t net_in = SimbricksNetIfInTimestamp(&nicif->net);
  uint64_t net_out = SimbricksNetIfOutNextSync(&nicif->net);
  uint64_t net = (net_in <= net_out ? net_in : net_out);

  uint64_t pcie_in = SimbricksPcieIfH2DInTimestamp(&nicif->pcie);
  uint64_t pcie_out = SimbricksPcieIfD2HOutNextSync(&nicif->pcie);
  uint64_t pcie = (pcie_in <= pcie_out ? pcie_in : pcie_out);

  return (net < pcie ? net : pcie);
}

#endif  // SIMBRICKS_NICIF_NICIF_H_
