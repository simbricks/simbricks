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


#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cassert>
#include <ctime>
#include <iostream>
#include <vector>

#include <simbricks/base/cxxatomicfix.h>

extern "C" {
#include <simbricks/mem/if.h>
#include <simbricks/nicif/nicif.h>
#include <simbricks/base/proto.h>
};


static int exiting = 0;
static uint64_t cur_ts = 0;

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
    fprintf(stderr, "main_time = %lu\n", cur_ts);
}

void handlePacket(SimbricksNetIf *netif, volatile struct SimbricksProtoNetMsgPacket *packet)
{
  volatile union SimbricksProtoMemM2H *m2h_msg = (SimbricksProtoMemM2H *)malloc(sizeof(SimbricksProtoMemM2H));
  volatile struct SimbricksProtoMemM2HWritecomp *wc = &m2h_msg->writecomp;
  wc->req_id = 1;
  volatile union SimbricksProtoNetMsg *msg = SimbricksNetIfOutAlloc(netif, cur_ts);
  if (msg == NULL)
    return;
  volatile struct SimbricksProtoNetMsgPacket *net_packet = &msg->packet;
  memcpy((void*)net_packet->data, (void*)m2h_msg, sizeof(SimbricksProtoMemM2H));
  packet->port = 0;
  packet->len = sizeof(SimbricksProtoMemM2H);
  SimbricksNetIfOutSend(netif, msg, SIMBRICKS_PROTO_NET_MSG_PACKET);
};

void PollN2M(SimbricksNetIf *netif, uint64_t cur_ts) {
  volatile union SimbricksProtoNetMsg *msg = SimbricksNetIfInPoll(netif, cur_ts);
  if (msg == NULL){
    return;
  }
  uint8_t type;

  type = SimbricksNetIfInType(netif, msg);
  switch (type) {
    case SIMBRICKS_PROTO_NET_MSG_PACKET:
      handlePacket(netif, &msg->packet);
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      break;

    default:
      fprintf(stderr, "poll_n2m: unsupported type=%u\n", type);
  }

  SimbricksNetIfInDone(netif, msg);
}

int main(int argc, char *argv[]) {
  
  signal(SIGINT, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  int sync_net = 1;
  uint64_t ts_a = 0;
  const char *shmPath;

  struct SimbricksBaseIfParams netParams;

  struct SimbricksNicIf netif;
  
  SimbricksNetIfDefaultParams(&netParams);

  if (argc < 4 || argc > 7) {
    fprintf(stderr,
            "Usage: netmem ETH-SOCKET"
            "SHM [SYNC-MODE] [START-TICK] [SYNC-PERIOD]"
            "[ETH-LATENCY]\n");
    return -1;
  }

  if (argc >= 5)
     cur_ts = strtoull(argv[4], NULL, 0);
  if (argc >= 6)
    netParams.sync_interval =
         strtoull(argv[5], NULL, 0) * 1000ULL;
  if (argc >= 7)
    netParams.link_latency = strtoull(argv[6], NULL, 0) * 1000ULL;

  netParams.sock_path = argv[1];
  shmPath = argv[2];

  netParams.sync_mode = kSimbricksBaseIfSyncOptional;

  netif.net.base.sync = sync_net;

  if(SimbricksNicIfInit(&netif, shmPath, &netParams,  NULL, NULL)){
    fprintf(stderr, "nicif init error happens");
    return -1;
  }

  fprintf(stderr, "start polling\n");
  while (!exiting){

    while (SimbricksNetIfOutSync(&netif.net, cur_ts)) {
      fprintf(stderr, "warn: SimbricksNicifSync failed (netif=%lu)\n", cur_ts);
    }

    do {
      PollN2M(&netif.net, cur_ts);
      ts_a = SimbricksNetIfInTimestamp(&netif.net);
    } while (!exiting && 
             ((sync_net && ts_a <= cur_ts)));

    if (sync_net)
      cur_ts = ts_a;

  }
  return 0;
}
