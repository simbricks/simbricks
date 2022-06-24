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

#ifndef SIMBRICKS_NETWORK_IF_H_
#define SIMBRICKS_NETWORK_IF_H_

#include <stddef.h>
#include <stdint.h>

#include <simbricks/base/generic.h>
#include <simbricks/network/proto.h>

struct SimbricksNetIf {
  struct SimbricksBaseIf base;
};

void SimbricksNetIfDefaultParams(struct SimbricksBaseIfParams *params);
int SimbricksNetIfInit(struct SimbricksNetIf *nsif,
                       struct SimbricksBaseIfParams *params,
                       const char *eth_socket_path, int *sync_eth);

/** Generate queue access functions */
SIMBRICKS_BASEIF_GENERIC(SimbricksNetIf, SimbricksProtoNetMsg, SimbricksNetIf);

#endif  // SIMBRICKS_NETWORK_IF_H_
