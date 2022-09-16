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

#include <arpa/inet.h>
#include <fcntl.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <netinet/udp.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <simbricks/mem/proto.h>
#include <simbricks/network/if.h>

#include "../netproto/netproto.h"

//  #define NETMEM_DEBUG 1

static int exiting = 0, sync_mem = 1;
static uint64_t cur_ts = 0;
uint8_t *mem_array;
uint64_t size;
uint64_t base_addr;
uint32_t ip_addr = 0x0A0B0C0D;

union mac_addr_ {
  uint64_t mac_64;
  uint8_t mac_byte[6];
};

union mac_addr_ mac_addr;

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  fprintf(stderr, "main_time = %lu\n", cur_ts);
}

int HandleRequest(struct SimbricksNetIf *netif,
                  volatile struct SimbricksProtoNetMsgPacket *packet) {
  volatile union SimbricksProtoNetMsg *msg_to =
      SimbricksNetIfOutAlloc(netif, cur_ts);
  if (msg_to == NULL) {
    return 0;
  }
  volatile struct SimbricksProtoNetMsgPacket *packet_to = &msg_to->packet;

  uint8_t type;
  uint16_t pkt_len = sizeof(struct ethhdr) + sizeof(struct iphdr) +
                     sizeof(struct udphdr) + sizeof(struct MemOp);
  uint16_t ip_total_len;
  struct ethhdr *eth_hdr = (struct ethhdr *)packet->data;
  struct iphdr *ip_hdr = (struct iphdr *)(eth_hdr + 1);
  struct udphdr *udp_hdr = (struct udphdr *)(ip_hdr + 1);
  struct MemOp *memop = (struct MemOp *)(udp_hdr + 1);
  void *data = (void *)(memop + 1);

  struct ethhdr *to_eth_hdr = (struct ethhdr *)packet_to->data;
  struct iphdr *to_ip_hdr = (struct iphdr *)(to_eth_hdr + 1);
  struct udphdr *to_udp_hdr = (struct udphdr *)(to_ip_hdr + 1);
  struct MemOp *to_memop = (struct MemOp *)(to_udp_hdr + 1);
  void *to_data = (void *)(to_memop + 1);

  type = memop->OpType;
  // Add Ethernet Header
  to_eth_hdr->h_proto = eth_hdr->h_proto;
  memcpy(to_eth_hdr->h_dest, eth_hdr->h_source, ETH_ALEN);
  memcpy(to_eth_hdr->h_source, mac_addr.mac_byte, ETH_ALEN);

  // Add IP header
  to_ip_hdr->saddr = ip_addr;
  to_ip_hdr->daddr = ip_hdr->saddr;
  ip_total_len =
      sizeof(struct iphdr) + sizeof(struct udphdr) + sizeof(struct MemOp);

  if (type == SIMBRICKS_PROTO_MEM_H2M_MSG_READ) {
    ip_total_len += memop->len;
  }
  to_ip_hdr->tot_len = htons(ip_total_len);

  // Add UDP header
  to_udp_hdr->uh_sport = udp_hdr->uh_dport;
  to_udp_hdr->uh_dport = udp_hdr->uh_sport;
  to_udp_hdr->uh_ulen = sizeof(struct udphdr) + sizeof(struct MemOp);
  if (type == SIMBRICKS_PROTO_MEM_H2M_MSG_READ) {
    to_udp_hdr->uh_ulen += memop->len;
  }

  packet_to->len = pkt_len;

  // Fill MemOp structure
  to_memop->req_id = memop->req_id;
  to_memop->as_id = memop->as_id;
  to_memop->addr = memop->addr;
  to_memop->len = memop->len;

  switch (type) {
    case SIMBRICKS_PROTO_MEM_H2M_MSG_READ:
#if NETMEM_DEBUG
      printf("received read request addr: 0x%lx size: 0x%x\n", memop->addr,
             memop->len);

#endif
      //  send read complete message
      to_memop->OpType = SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP;

      memcpy((void *)to_data, &mem_array[memop->addr], memop->len);

      packet_to->len += memop->len;
      break;
    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE:
#if NETMEM_DEBUG
      printf("received write request addr: 0x%lx size: 0x%x\n", memop->addr,
             memop->len);
#endif
      //  write the data in local memory
      memcpy(&mem_array[memop->addr], data, memop->len);

      // send write complete message
      to_memop->OpType = SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP;

      break;
    default:
      fprintf(stderr, "poll_n2m: unsupported type=%u\n", type);
  }

#if NETMEM_DEBUG
  int i;
  printf("response to_eth_source: ");
  for (i = 0; i < ETH_ALEN; i++) {
    printf("%X: ", to_eth_hdr->h_source[i]);
  }
  printf("--> to_eth_dest: ");
  for (i = 0; i < ETH_ALEN; i++) {
    printf("%X: ", to_eth_hdr->h_dest[i]);
  }
  printf("\n");
#endif

  SimbricksNetIfOutSend(netif, msg_to, SIMBRICKS_PROTO_NET_MSG_PACKET);
  return 1;
}

void PollN2M(struct SimbricksNetIf *netif, uint64_t cur_ts) {
  volatile union SimbricksProtoNetMsg *msg =
      SimbricksNetIfInPoll(netif, cur_ts);

  if (msg == NULL) {
    return;
  }

  uint8_t type;
  volatile struct SimbricksProtoNetMsgPacket *packet = &msg->packet;

  type = SimbricksNetIfInType(netif, msg);
  switch (type) {
    case SIMBRICKS_PROTO_NET_MSG_PACKET:
#if NETMEM_DEBUG
      printf("received network packet\n");
#endif
      if (!HandleRequest(netif, packet)) {
        return;
      }
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

  uint64_t next_ts = 0;
  struct SimbricksBaseIfParams netParams;
  struct SimbricksNetIf netif;
  const char *shmPath;

  SimbricksNetIfDefaultParams(&netParams);

  if (argc < 7 || argc > 11) {
    fprintf(stderr,
            "Usage: netmem [SIZE] [BASE-ADDR] [ASID] [ETH-SOCKET] "
            "[SHM] [MAC-ADDR] [SYNC-MODE] [START-TICK] [SYNC-PERIOD] "
            "[ETH-LATENCY]\n");
    return -1;
  }
  if (argc >= 9)
    cur_ts = strtoull(argv[8], NULL, 0);
  if (argc >= 10)
    netParams.sync_interval = strtoull(argv[9], NULL, 0) * 1000ULL;
  if (argc >= 11)
    netParams.link_latency = strtoull(argv[10], NULL, 0) * 1000ULL;

  size = strtoull(argv[1], NULL, 0);
  base_addr = strtoull(argv[2], NULL, 0);
  netParams.sock_path = argv[4];
  shmPath = argv[5];
  mac_addr.mac_64 = strtoull(argv[6], NULL, 16);
  printf("mac_byte: %lx\n", mac_addr.mac_64);
  printf("mac_8: %X:%X:%X:%X:%X:%X\n", mac_addr.mac_byte[0],
         mac_addr.mac_byte[1], mac_addr.mac_byte[2], mac_addr.mac_byte[3],
         mac_addr.mac_byte[4], mac_addr.mac_byte[5]);

  netParams.sync_mode = kSimbricksBaseIfSyncOptional;
  netParams.blocking_conn = false;

  mem_array = (uint8_t *)malloc(size * sizeof(uint8_t));

  if (!mem_array) {
    perror("no array allocated\n");
  }

  size_t shm_size = 0;
  shm_size += netParams.in_num_entries * netParams.in_entries_size;
  shm_size += netParams.out_num_entries * netParams.out_entries_size;

  struct SimbricksBaseIfSHMPool pool_;
  memset(&pool_, 0, sizeof(pool_));

  if (SimbricksBaseIfInit(&netif.base, &netParams)) {
    perror("Init: SimbricksBaseIfInit failed\n");
    return EXIT_FAILURE;
  }

  if (SimbricksBaseIfSHMPoolCreate(&pool_, shmPath, shm_size) != 0) {
    perror("NetMemIfInit: SimbricksBaseIfSHMPoolCreate failed");
    return false;
  }

  if (SimbricksBaseIfListen(&netif.base, &pool_)) {
    perror("SimbricksBaseIfConnect failed");
    return false;
  }

  struct SimBricksBaseIfEstablishData ests[1];
  struct SimbricksProtoNetIntro intro;
  ests[0].base_if = &netif.base;
  ests[0].tx_intro = &intro;
  ests[0].tx_intro_len = sizeof(intro);
  ests[0].rx_intro = &intro;
  ests[0].rx_intro_len = sizeof(intro);

  if (SimBricksBaseIfEstablish(ests, 1)) {
    fprintf(stderr, "SimBricksBaseIfEstablish failed\n");
    return false;
  }
  sync_mem = SimbricksBaseIfSyncEnabled(&netif.base);

  printf("start polling\n");
  while (!exiting) {
    while (SimbricksNetIfOutSync(&netif, cur_ts)) {
      fprintf(stderr, "warn: SimbricksNetIfSync failed (t=%lu)\n", cur_ts);
    }

    do {
      PollN2M(&netif, cur_ts);

      if (sync_mem) {
        next_ts = SimbricksNetIfInTimestamp(&netif);
      }
    } while (!exiting && next_ts <= cur_ts);

    cur_ts = next_ts;
  }
  return 0;
}
