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

bool MemifInit(struct SimbricksMemIf *memif, const char *shm_path,
                struct SimbricksBaseIfParams *memParams) {
  
  struct SimbricksBaseIf *membase = &memif->base;
  struct SimbricksBaseIfSHMPool pool_;
  memset(&pool_, 0, sizeof(pool_));
  
  struct SimBricksBaseIfEstablishData ests[1];
  struct SimbricksProtoMemHostIntro intro;
  unsigned n_bifs = 0;

  memset(&intro, 0, sizeof(intro));
  ests[n_bifs].base_if = membase;
  ests[n_bifs].tx_intro = &intro;
  ests[n_bifs].tx_intro_len = sizeof(intro);
  ests[n_bifs].rx_intro = &intro;
  ests[n_bifs].rx_intro_len = sizeof(intro);
  n_bifs++;
  
  if (SimbricksBaseIfInit(membase, memParams)) {
    perror("Init: SimbricksBaseIfInit failed");
  }

  std::string shm_path_ = shm_path;

  if (SimbricksBaseIfSHMPoolCreate(
          &pool_, shm_path_.c_str(),
          SimbricksBaseIfSHMSize(&membase->params)) != 0) {
    perror("MemifInit: SimbricksBaseIfSHMPoolCreate failed");
    return false;
  }

  if (SimbricksBaseIfListen(membase, &pool_) != 0) {
    perror("MemifInit: SimbricksBaseIfListen failed");
    return false;
  }

  if (SimBricksBaseIfEstablish(ests, 1)) {
    fprintf(stderr, "SimBricksBaseIfEstablish failed\n");
    return false;
  }

  printf("done connecting\n");
  return true;
}

void EthSend(SimbricksNetIf *netif, volatile union SimbricksProtoMemH2M *data, size_t len) {
  volatile union SimbricksProtoNetMsg *msg = SimbricksNetIfOutAlloc(netif, cur_ts);
  if (msg == NULL)
    return;
  volatile struct SimbricksProtoNetMsgPacket *packet = &msg->packet;
  packet->port = 0;
  packet->len = len;
  memcpy((void *)packet->data, (void *)data, len);
  SimbricksNetIfOutSend(netif, msg, SIMBRICKS_PROTO_NET_MSG_PACKET);
}

void EthRx(SimbricksMemIf *memif, volatile struct SimbricksProtoNetMsgPacket *packet) {
  uint8_t type;
  volatile union SimbricksProtoMemM2H *msg = SimbricksMemIfM2HOutAlloc(memif, cur_ts);
  if (msg == NULL)
    return;
  volatile struct SimbricksProtoMemM2HReadcomp *rc;
  volatile struct SimbricksProtoMemM2HWritecomp *wc;
  type = SimbricksMemIfM2HInType(memif, msg);
  
  switch (type){
    case SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP:
      rc = &msg->readcomp;
      memcpy((void*)msg, (void*)packet->data, packet->len);
      SimbricksMemIfM2HOutSend(memif, msg, SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP);
      break;
  
    case SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP:
      wc = &msg->writecomp;
      memcpy((void*)msg, (void *)packet->data, packet->len);
      SimbricksMemIfM2HOutSend(memif, msg, SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP);
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      break;

    default:
      fprintf(stderr, "poll_m2h: unsupported type=%u\n", type);
  }

}

void PollM2H(struct SimbricksMemIf *memif, SimbricksNetIf *netif, uint64_t cur_ts) {
  volatile union SimbricksProtoNetMsg *msg = SimbricksNetIfInPoll(netif, cur_ts);
  if (msg == NULL){
    return;
  }
  uint8_t type;

  type = SimbricksNetIfInType(netif, msg);
  switch (type) {
    case SIMBRICKS_PROTO_NET_MSG_PACKET:
      EthRx(memif, &msg->packet);
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      break;

    default:
      fprintf(stderr, "poll_m2h: unsupported type=%u\n", type);
  }

  SimbricksNetIfInDone(netif, msg);
}

void PollH2M(struct SimbricksMemIf *memif, SimbricksNetIf *netif, uint64_t cur_ts) {
  volatile union SimbricksProtoMemH2M *msg = SimbricksMemIfH2MInPoll(memif, cur_ts);

  if (msg == NULL){
    return;
  }
  uint8_t type;

  type = SimbricksMemIfH2MInType(memif, msg);
  switch (type) {
    
    case SIMBRICKS_PROTO_MEM_H2M_MSG_READ:
      EthSend(netif, msg, sizeof(SimbricksProtoMemH2M));
      break;

    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE:
      EthSend(netif, msg, sizeof(SimbricksProtoMemH2M));
      break;
    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      break;
    default:
      fprintf(stderr, "poll_h2m: unsupported type=%u\n", type);
  }

  SimbricksMemIfH2MInDone(memif, msg);
}

int main(int argc, char *argv[]) {
  
  signal(SIGINT, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  int sync_mem = 1, sync_net = 1;
  uint64_t ts_a = 0;
  uint64_t ts_b = 0;
  const char *shmPath;

  struct SimbricksBaseIfParams memParams;
  struct SimbricksBaseIfParams netParams;

  struct SimbricksMemIf memif;
  struct SimbricksNicIf netif;
  
  SimbricksMemIfDefaultParams(&memParams);
  SimbricksNetIfDefaultParams(&netParams);

  if (argc < 4 || argc > 10) {
    fprintf(stderr,
            "Usage: memnic MEM-SOCKET NET-SOCKET"
            "SHM [SYNC-MODE] [START-TICK] [SYNC-PERIOD] [MEM-LATENCY]"
            "[ETH-LATENCY]\n");
    return -1;
  }

  if (argc >= 6)
     cur_ts = strtoull(argv[5], NULL, 0);
  if (argc >= 7)
    memParams.sync_interval = netParams.sync_interval =
         strtoull(argv[6], NULL, 0) * 1000ULL;
  if (argc >= 8)
    memParams.link_latency = strtoull(argv[7], NULL, 0) * 1000ULL;
  if (argc >= 9)
    netParams.link_latency = strtoull(argv[8], NULL, 0) * 1000ULL;

  memParams.sock_path = argv[1];
  netParams.sock_path = argv[2];
  shmPath = argv[3];

  memParams.sync_mode = kSimbricksBaseIfSyncOptional;
  netParams.sync_mode = kSimbricksBaseIfSyncOptional;
  memParams.blocking_conn = false;
  memif.base.sync = sync_mem;
  netif.net.base.sync = sync_net;

  if(SimbricksNicIfInit(&netif, shmPath, &netParams,  NULL, NULL)){
    fprintf(stderr, "nicif init error happens");
    return -1;
  }

  if (!MemifInit(&memif, shmPath, &memParams)){
    fprintf(stderr, "memif init error happens");
    return -1;
  }

  

  fprintf(stderr, "start polling\n");
  while (!exiting){
    while (SimbricksMemIfM2HOutSync(&memif, cur_ts)) {
      fprintf(stderr, "warn: SimbricksMemnetifSync failed (memif=%lu)\n", cur_ts);
    }
    while (SimbricksNetIfOutSync(&netif.net, cur_ts)) {
      fprintf(stderr, "warn: SimbricksNicifSync failed (netif=%lu)\n", cur_ts);
    }
    
    do {
      PollH2M(&memif, &netif.net, cur_ts);
      PollM2H(&memif, &netif.net, cur_ts);
      ts_a = SimbricksMemIfH2MInTimestamp(&memif);
      ts_b = SimbricksNetIfInTimestamp(&netif.net);
    } while (!exiting && 
             ((sync_mem && ts_a <= cur_ts) || (sync_net && ts_b <= cur_ts)));

    if (sync_mem && sync_net)
      cur_ts = ts_a <= ts_b ? ts_a : ts_b;
    else if (sync_mem)
      cur_ts = ts_a;
    else if (sync_net)
      cur_ts = ts_b;

  }
  return 0;
}
