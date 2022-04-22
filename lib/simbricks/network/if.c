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

#include "lib/simbricks/network/if.h"

#include <poll.h>
#include <stdio.h>
#include <string.h>

void SimbricksNetIfDefaultParams(struct SimbricksBaseIfParams *params)
{
  SimbricksBaseIfDefaultParams(params);
  params->in_entries_size = params->out_entries_size = 1536 + 64;
  params->upper_layer_proto = SIMBRICKS_PROTO_ID_NET;
}

int SimbricksNetIfInit(struct SimbricksNetIf *nsif,
                       struct SimbricksBaseIfParams *params,
                       const char *eth_socket_path,
                       int *sync_eth)
{
  // some threaded code using this interface
  struct SimbricksBaseIfParams params_ = *params;
  struct SimbricksBaseIf *bif = &nsif->base;

  if (sync_eth && *sync_eth)
    params_.sync_mode = kSimbricksBaseIfSyncOptional;
  else
    params_.sync_mode = kSimbricksBaseIfSyncDisabled;

  params_.sock_path = eth_socket_path;

  if (SimbricksBaseIfInit(bif, &params_)) {
    perror("SimbricksNetIfInit: SimbricksBaseIfInit failed");
    return -1;
  }

  if (SimbricksBaseIfConnect(bif)) {
    perror("SimbricksNetIfInit: SimbricksBaseIfConnect failed");
    return -1;
  }

  if (SimbricksBaseIfConnsWait(&bif, 1)) {
    perror("SimbricksNetIfInit: SimbricksBaseIfConnect failed");
    return -1;
  }

  struct SimbricksProtoNetIntro intro;
  memset(&intro, 0, sizeof(intro));
  if (SimbricksBaseIfIntroSend(bif, &intro, sizeof(intro))) {
    perror("SimbricksNetIfInit: SimbricksBaseIfIntroSend failed");
    return -1;
  }

  struct pollfd pfd;
  pfd.fd = SimbricksBaseIfIntroFd(bif);
  pfd.events = POLLIN;
  pfd.revents = 0;
  if (poll(&pfd, 1, -1) != 1) {
    perror("SimbricksNetIfInit: poll failed");
    return -1;
  }

  size_t plen = sizeof(intro);
  if (SimbricksBaseIfIntroRecv(bif, &intro, &plen)) {
    perror("SimbricksNetIfInit: SimbricksBaseIfIntroRecv failed");
    return -1;
  }

  if (sync_eth)
    *sync_eth = SimbricksBaseIfSyncEnabled(bif);

  return 0;
}