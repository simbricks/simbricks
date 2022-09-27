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


#include <arpa/inet.h>
#include<netinet/udp.h>
#include <linux/ip.h>
#include <linux/if_ether.h>

#include <simbricks/base/cxxatomicfix.h>

extern "C" {
#include <simbricks/mem/if.h>
#include <simbricks/nicif/nicif.h>
#include <simbricks/mem/memop.h>
};

#define MEMNIC_DEBUG 1

static int exiting = 0;
static uint64_t cur_ts = 0;
uint16_t src_port = 1;
uint16_t dest_port = 1;
uint32_t ip_addr = 0x0F0E0D0C;
uint64_t mac_addr = 0;


static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
    fprintf(stderr, "main_time = %lu\n", cur_ts);
}

bool MemNicIfInit(struct SimbricksMemIf *memif, struct SimbricksNetIf *netif,
                  const char *shm_path,
                  struct SimbricksBaseIfParams *memParams,
                  struct SimbricksBaseIfParams *netParams) {

  struct SimbricksBaseIf *membase = &memif->base;
  struct SimbricksBaseIf *netbase = &netif->base;

  // first allocate pool
  size_t shm_size = 0;
  if (memParams){
    shm_size += memParams->in_num_entries * memParams->in_entries_size;
    shm_size += memParams->out_num_entries * memParams->out_entries_size;
  }
  if (netParams){
    shm_size += netParams->in_num_entries * netParams->in_entries_size;
    shm_size += netParams->out_num_entries * netParams->out_entries_size;
  }
  
  std::string shm_path_ = shm_path;
  struct SimbricksBaseIfSHMPool pool_;
  memset(&pool_, 0, sizeof(pool_));

  if (SimbricksBaseIfSHMPoolCreate(&pool_, shm_path_.c_str(), shm_size) !=
      0) {
      perror("MemNicIfInit: SimbricksBaseIfSHMPoolCreate failed");
      return false;
    }

  struct SimBricksBaseIfEstablishData ests[2];
  struct SimbricksProtoMemHostIntro mem_intro;
  struct SimbricksProtoNetIntro net_intro;
  unsigned n_bifs = 0;

  memset(&net_intro, 0, sizeof(net_intro));

  // MemIf Init
  if (SimbricksBaseIfInit(membase, memParams)) {
    perror("MemIfInit: SimbricksBaseIfInit failed");
  }

  if (SimbricksBaseIfListen(membase, &pool_) != 0) {
    perror("MemifInit: SimbricksBaseIfListen failed");
    return false;
  }

  memset(&mem_intro, 0, sizeof(mem_intro));
  ests[n_bifs].base_if = membase;
  ests[n_bifs].tx_intro = &mem_intro;
  ests[n_bifs].tx_intro_len = sizeof(mem_intro);
  ests[n_bifs].rx_intro = &mem_intro;
  ests[n_bifs].rx_intro_len = sizeof(mem_intro);
  n_bifs++;

  // NetIf Init
  if (SimbricksBaseIfInit(netbase, netParams)) {
    perror("NetIfInit: SimbricksBaseIfInit failed");
  }

  if (SimbricksBaseIfListen(netbase, &pool_) != 0) {
    perror("NetIfInit: SimbricksBaseIfListen failed");
    return false;
  }

  memset(&net_intro, 0, sizeof(net_intro));
  ests[n_bifs].base_if = netbase;
  ests[n_bifs].tx_intro = &net_intro;
  ests[n_bifs].tx_intro_len = sizeof(net_intro);
  ests[n_bifs].rx_intro = &net_intro;
  ests[n_bifs].rx_intro_len = sizeof(net_intro);
  n_bifs++;



  if (SimBricksBaseIfEstablish(ests, 2)) {
    fprintf(stderr, "SimBricksBaseIfEstablish failed\n");
    return false;
  }

  printf("done connecting\n");
  return true;
}

static inline int SimbricksMemNicIfSync(struct SimbricksMemIf *memif,
                                        struct SimbricksNetIf *netif,
                                        uint64_t cur_ts) {
  return ((SimbricksMemIfM2HOutSync(memif, cur_ts) == 0 &&
           SimbricksNetIfOutSync(netif, cur_ts) == 0)
              ? 0
              : -1);
}

static inline uint64_t SimbricksMemNicIfNextTimestamp(
    struct SimbricksMemIf *memif, struct SimbricksNetIf *netif) {
  uint64_t net_in = SimbricksNetIfInTimestamp(netif);
  uint64_t mem_in = SimbricksMemIfH2MInTimestamp(memif);

  return (net_in < mem_in ? net_in : mem_in);
}

void ForwardToETH(SimbricksNetIf *netif, volatile union SimbricksProtoMemH2M *data, uint8_t type) {
  
  volatile union SimbricksProtoNetMsg *msg = SimbricksNetIfOutAlloc(netif, cur_ts);
  if (msg == NULL)
    return;

  volatile struct SimbricksProtoNetMsgPacket *packet = &msg->packet;

  // Add Ethernet header
  struct ethhdr *eth_hdr = (struct ethhdr *)packet->data;
  uint64_t dest_mac = 0xFFFFFFFF;
  memcpy(eth_hdr->h_source, &mac_addr, sizeof(uint64_t));
  memcpy(eth_hdr->h_dest, &dest_mac, sizeof(uint64_t)); // Keep destination to broadcast for now
  eth_hdr->h_proto = htons(ETH_P_IP);

  // Add IP header
  struct iphdr *ip_hdr = (struct iphdr *)(eth_hdr + 1);
  ip_hdr->daddr = 0xFFFFFFFF;
  ip_hdr->saddr = ip_addr;
  ip_hdr->tot_len = sizeof(struct iphdr) + sizeof(struct udphdr) + sizeof(struct MemOp);
  if (type == SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE){
    ip_hdr->tot_len += data->write.len;
  }

  // Add UDP header
  struct udphdr *udp_hdr = (struct udphdr *)(ip_hdr + 1);
  udp_hdr->uh_sport = src_port;
  udp_hdr->uh_dport = dest_port;
  udp_hdr->uh_ulen = sizeof(struct udphdr) + sizeof(struct MemOp);
  if (type == SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE){
    udp_hdr->uh_ulen += data->write.len;
  }
  udp_hdr->uh_sum = 0; // To update later

  // Fill the MemOps struct in the payload
  struct MemOp *memop = (struct MemOp *)(udp_hdr + 1);
  void *payload;
  switch (type) {
    case SIMBRICKS_PROTO_MEM_H2M_MSG_READ:
      memop->OpType = type;
      memop->req_id = data->read.req_id;
      memop->as_id = data->read.as_id;
      memop->addr = data->read.addr;
      memop->len = data->read.len;
      break;
    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE:
      memop->OpType = type;
      memop->req_id = data->write.req_id;
      memop->as_id = data->write.as_id;
      memop->addr = data->write.addr;
      memop->len = data->write.len;
      payload = (void *)(memop + 1);
      memcpy((void *)payload, (void *)data->write.data, data->write.len);
      break;

    default:
      fprintf(stderr, "ForwardToETH: unsupported type=%u\n", type);

  }
  

  SimbricksNetIfOutSend(netif, msg, SIMBRICKS_PROTO_NET_MSG_PACKET);
}


void ForwardToMEM(SimbricksMemIf *memif, volatile struct SimbricksProtoNetMsgPacket *packet) {

  volatile union SimbricksProtoMemM2H *msg = SimbricksMemIfM2HOutAlloc(memif, cur_ts);

  if (msg == NULL)
    return;
  
  
  uint8_t type;
  struct ethhdr *eth_hdr = (struct ethhdr *)packet->data;
  struct iphdr *ip_hdr = (struct iphdr *)(eth_hdr + 1);
  struct udphdr *udp_hdr = (struct udphdr *)(ip_hdr + 1);
  struct MemOp *memop = (struct MemOp *)(udp_hdr + 1);
  void *data = (void *)(memop + 1);

  type = memop->OpType;

  switch (type){
    case SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP:
      volatile struct SimbricksProtoMemM2HReadcomp *rc;
      rc = &msg->readcomp;
      rc->req_id = memop->req_id;

      memcpy((void*)rc->data, (void*)data, memop->len);
      SimbricksMemIfM2HOutSend(memif, msg, SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP);
      break;
  
    case SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP:
      volatile struct SimbricksProtoMemM2HWritecomp *wc;
      wc = &msg->writecomp;
      wc->req_id = memop->req_id;

      SimbricksMemIfM2HOutSend(memif, msg, SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP);
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      break;

    default:
      fprintf(stderr, "poll_m2h: unsupported type=%u\n", type);
  }

}

void PollN2M(SimbricksNetIf *netif, struct SimbricksMemIf *memif, uint64_t cur_ts) {
  volatile union SimbricksProtoNetMsg *msg = SimbricksNetIfInPoll(netif, cur_ts);
  if (msg == NULL){
    return;
  }
  uint8_t type;

  type = SimbricksNetIfInType(netif, msg);
  switch (type) {
    case SIMBRICKS_PROTO_NET_MSG_PACKET:
      ForwardToMEM(memif, &msg->packet);
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      break;

    default:
      fprintf(stderr, "poll_n2m: unsupported type=%u\n", type);
  }

  SimbricksNetIfInDone(netif, msg);
}

void PollH2M(struct SimbricksMemIf *memif, SimbricksNetIf *netif, uint64_t cur_ts) {
  volatile union SimbricksProtoMemH2M *msg = SimbricksMemIfH2MInPoll(memif, cur_ts);

  if (msg == NULL) {
    return;
  }
  uint8_t type;

  type = SimbricksMemIfH2MInType(memif, msg);
  switch (type) {
    
    case SIMBRICKS_PROTO_MEM_H2M_MSG_READ:
      ForwardToETH(netif, msg, type);
      break;

    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE:
      ForwardToETH(netif, msg, type);
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

  uint64_t ts_mem = 0;
  uint64_t ts_net = 0;
  const char *shmPath;

  struct SimbricksBaseIfParams memParams;
  struct SimbricksBaseIfParams netParams;

  struct SimbricksMemIf memif;
  struct SimbricksNetIf netif;
  
  SimbricksMemIfDefaultParams(&memParams);
  SimbricksNetIfDefaultParams(&netParams);

  printf("sizeof(struct SimbricksProtoMemH2MWrite): %lu\n",
         sizeof(struct SimbricksProtoMemH2MWrite));

  
  if (argc < 4 || argc > 10) {
    fprintf(stderr,
            "Usage: memnic MEM-SOCKET NET-SOCKET"
            "SHM [MAC-ADDR] [SYNC-MODE] [START-TICK] [SYNC-PERIOD] [MEM-LATENCY]"
            "[ETH-LATENCY]\n");
    return -1;
  }

  if (argc >= 7)
     cur_ts = strtoull(argv[6], NULL, 0);
  if (argc >= 8)
    memParams.sync_interval = netParams.sync_interval =
         strtoull(argv[7], NULL, 0) * 1000ULL;
  if (argc >= 9)
    memParams.link_latency = strtoull(argv[8], NULL, 0) * 1000ULL;
  if (argc >= 10)
    netParams.link_latency = strtoull(argv[9], NULL, 0) * 1000ULL;

  memParams.sock_path = argv[1];
  netParams.sock_path = argv[2];
  shmPath = argv[3];
  mac_addr = strtoull(argv[4], NULL, 16);

  memParams.sync_mode = kSimbricksBaseIfSyncOptional;
  netParams.sync_mode = kSimbricksBaseIfSyncOptional;
  memParams.blocking_conn = false;
  memif.base.sync = sync_mem;
  netif.base.sync = sync_net;


  if (!MemNicIfInit(&memif, &netif, shmPath, &memParams, &netParams)){
    fprintf(stderr, "MemNicIf init error happens");
    return -1;
  }

  

  fprintf(stderr, "start polling\n");
  while (!exiting){
    while (SimbricksMemNicIfSync(&memif, &netif, cur_ts)) {
      fprintf(stderr, "warn: SimbricksMemNicIfSync failed (memif=%lu)\n", cur_ts);
    }

    do {
      PollH2M(&memif, &netif, cur_ts);
      PollN2M(&netif, &memif, cur_ts);

      ts_mem = SimbricksMemIfH2MInTimestamp(&memif);
      ts_net = SimbricksNetIfInTimestamp(&netif);

    } while (!exiting && 
             ((sync_mem && ts_mem <= cur_ts) || (sync_net && ts_net <= cur_ts)));

    if (sync_mem && sync_net)
      cur_ts = ts_mem <= ts_net ? ts_mem : ts_net;
    else if (sync_mem)
      cur_ts = ts_mem;
    else if (sync_net)
      cur_ts = ts_net;

  }

  // Todo: cleanup

  return 0;
}
