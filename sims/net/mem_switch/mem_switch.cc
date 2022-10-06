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

#include <arpa/inet.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <pcap/pcap.h>
#include <unistd.h>

#include <cassert>
#include <climits>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

#include <simbricks/base/cxxatomicfix.h>
extern "C" {
#include <simbricks/network/if.h>
#include <simbricks/nicif/nicif.h>
#include <simbricks/mem/memop.h>
};

// #define NETSWITCH_DEBUG
#define NETSWITCH_STAT

struct SimbricksBaseIfParams netParams;
static pcap_dumper_t *dumpfile = nullptr;

#ifdef NETSWITCH_STAT
#endif

#ifdef NETSWITCH_STAT
static uint64_t d2n_poll_total = 0;
static uint64_t d2n_poll_suc = 0;
static uint64_t d2n_poll_sync = 0;

static uint64_t s_d2n_poll_total = 0;
static uint64_t s_d2n_poll_suc = 0;
static uint64_t s_d2n_poll_sync = 0;

static int stat_flag = 0;
#endif
union ether_addr
{
  uint64_t ether_addr_64;
  uint8_t ether_addr_octet[ETH_ALEN];
} __attribute__ ((__packed__));

struct table_entry {
  uint64_t as_id;
  uint64_t vaddr_start;
  uint64_t vaddr_end;
  union ether_addr node_mac;
  uint64_t phys_start;
};

std::vector<struct table_entry> map_table;


/* MAC address type */
struct MAC {
  const uint8_t *data;

  explicit MAC(const uint8_t *data) : data(data) {
  }

  bool operator==(const MAC &other) const {
    for (int i = 0; i < 6; i++) {
      if (data[i] != other.data[i]) {
        return false;
      }
    }
    return true;
  }

  MAC operator=(const uint8_t *other) const {
    MAC mac(other);
    return mac;
  }
};
namespace std {
template <>
struct hash<MAC> {
  size_t operator()(const MAC &m) const {
    size_t res = 0;
    for (int i = 0; i < 6; i++) {
      res = (res << 4) | (res ^ m.data[i]);
    }
    return res;
  }
};
}  // namespace std

/** Normal network switch port (conneting to a NIC) */
class NetPort {
 public:
  enum RxPollState {
    kRxPollSuccess = 0,
    kRxPollFail = 1,
    kRxPollSync = 2,
  };
  struct SimbricksNetIf netif_;
  const char *path_;

 protected:
  volatile union SimbricksProtoNetMsg *rx_;
  int sync_;

  bool Init() {
    struct SimbricksBaseIfParams params = netParams;
    params.sync_mode =
        (sync_ ? kSimbricksBaseIfSyncOptional : kSimbricksBaseIfSyncDisabled);
    params.sock_path = path_;
    params.blocking_conn = false;

    if (SimbricksBaseIfInit(&netif_.base, &params)) {
      perror("Init: SimbricksBaseIfInit failed");
      return false;
    }

    return true;
  }

 public:
  NetPort(const char *path, int sync) : rx_(nullptr), sync_(sync), path_(path) {
    memset(&netif_, 0, sizeof(netif_));
  }

  NetPort(const NetPort &other)
      : netif_(other.netif_),
        rx_(other.rx_),
        sync_(other.sync_),
        path_(other.path_) {
  }

  virtual bool Prepare() {
    if (!Init())
      return false;

    if (SimbricksBaseIfConnect(&netif_.base)) {
      perror("Prepare: SimbricksBaseIfConnect failed");
      return false;
    }

    return true;
  }

  virtual void Prepared() {
    sync_ = SimbricksBaseIfSyncEnabled(&netif_.base);
  }

  bool IsSync() {
    return sync_;
  }

  void Sync(uint64_t cur_ts) {
    while (SimbricksNetIfOutSync(&netif_, cur_ts)) {
    }
  }

  uint64_t NextTimestamp() {
    return SimbricksNetIfInTimestamp(&netif_);
  }

  enum RxPollState RxPacket(const void *&data, size_t &len, uint64_t cur_ts) {
    assert(rx_ == nullptr);

    rx_ = SimbricksNetIfInPoll(&netif_, cur_ts);
    if (!rx_)
      return kRxPollFail;

    uint8_t type = SimbricksNetIfInType(&netif_, rx_);
    if (type == SIMBRICKS_PROTO_NET_MSG_PACKET) {
      data = (const void *)rx_->packet.data;
      len = rx_->packet.len;
      return kRxPollSuccess;
    } else if (type == SIMBRICKS_PROTO_MSG_TYPE_SYNC) {
      return kRxPollSync;
    } else {
      fprintf(stderr, "switch_pkt: unsupported type=%u\n", type);
      abort();
    }
  }

  void RxDone() {
    assert(rx_ != nullptr);

    SimbricksNetIfInDone(&netif_, rx_);
    rx_ = nullptr;
  }

  bool TxPacket(const void *data, size_t len, uint64_t cur_ts) {
    volatile union SimbricksProtoNetMsg *msg_to =
        SimbricksNetIfOutAlloc(&netif_, cur_ts);
    if (!msg_to && !sync_) {
      return false;
    } else if (!msg_to && sync_) {
      while (!msg_to)
        msg_to = SimbricksNetIfOutAlloc(&netif_, cur_ts);
    }
    volatile struct SimbricksProtoNetMsgPacket *rx;
    rx = &msg_to->packet;
    rx->len = len;
    rx->port = 0;
    memcpy((void *)rx->data, data, len);

    SimbricksNetIfOutSend(&netif_, msg_to, SIMBRICKS_PROTO_NET_MSG_PACKET);
    return true;
  }
};

/** Listening switch port (connected to by another network) */
class NetListenPort : public NetPort {
 protected:
  struct SimbricksBaseIfSHMPool pool_;

 public:
  NetListenPort(const char *path, int sync) : NetPort(path, sync) {
    memset(&pool_, 0, sizeof(pool_));
  }

  NetListenPort(const NetListenPort &other)
      : NetPort(other), pool_(other.pool_) {
  }

  bool Prepare() override {
    if (!Init())
      return false;

    std::string shm_path = path_;
    shm_path += "-shm";

    if (SimbricksBaseIfSHMPoolCreate(
            &pool_, shm_path.c_str(),
            SimbricksBaseIfSHMSize(&netif_.base.params)) != 0) {
      perror("Prepare: SimbricksBaseIfSHMPoolCreate failed");
      return false;
    }

    if (SimbricksBaseIfListen(&netif_.base, &pool_) != 0) {
      perror("Prepare: SimbricksBaseIfListen failed");
      return false;
    }

    return true;
  }
};

static bool ConnectAll(std::vector<NetPort *> ports) {
  size_t n = ports.size();
  struct SimBricksBaseIfEstablishData ests[n];
  struct SimbricksProtoNetIntro intro;

  printf("start connecting...\n");
  for (size_t i = 0; i < n; i++) {
    NetPort *p = ports[i];
    ests[i].base_if = &p->netif_.base;
    ests[i].tx_intro = &intro;
    ests[i].tx_intro_len = sizeof(intro);
    ests[i].rx_intro = &intro;
    ests[i].rx_intro_len = sizeof(intro);

    if (!p->Prepare())
      return false;
  }

  if (SimBricksBaseIfEstablish(ests, n)) {
    fprintf(stderr, "ConnectAll: SimBricksBaseIfEstablish failed\n");
    return false;
  }

  printf("done connecting\n");
  return true;
}

/* Global variables */
static uint64_t cur_ts = 0;
static int exiting = 0;
static const uint8_t bcast[6] = {0xFF};
static const MAC bcast_addr(bcast);
static std::vector<NetPort *> ports;
static std::unordered_map<MAC, int> mac_table;

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  fprintf(stderr, "main_time = %lu\n", cur_ts);
}

#ifdef NETSWITCH_STAT
static void sigusr2_handler(int dummy) {
  stat_flag = 1;
}
#endif

static void forward_pkt(const void *pkt_data, size_t pkt_len, size_t port_id,
                        size_t iport_id) {
  struct pcap_pkthdr ph;
  NetPort &dest_port = *ports[port_id];

  // log to pcap file if initialized
  if (dumpfile) {
    memset(&ph, 0, sizeof(ph));
    ph.ts.tv_sec = cur_ts / 1000000000000ULL;
    ph.ts.tv_usec = (cur_ts % 1000000000000ULL) / 1000ULL;
    ph.caplen = pkt_len;
    ph.len = pkt_len;
    pcap_dump((unsigned char *)dumpfile, &ph, (unsigned char *)pkt_data);
  }
  // print sending tick: [packet type] source_IP -> dest_IP len:

#ifdef NETSWITCH_DEBUG
  uint16_t eth_proto;
  struct ethhdr *hdr;
  struct iphdr *iph;
  hdr = (struct ethhdr *)pkt_data;
  eth_proto = ntohs(hdr->h_proto);
  iph = (struct iphdr *)(hdr + 1);
  int i;

  fprintf(stderr, "%20lu: [P %zu -> %zu] ", cur_ts, iport_id,
          port_id);
  fprintf(stderr, "src_mac: ");
  for (i = 0; i < ETH_ALEN; i++){
    fprintf(stderr, "%X:", hdr->h_source[i]);
  }
  fprintf(stderr, " -> ");
  for (i = 0; i < ETH_ALEN; i++){
    fprintf(stderr, "%X:", hdr->h_dest[i]);
  }
  
  if (eth_proto == ETH_P_IP) {
    fprintf(stderr, "[ IP] ");
    fprintf(stderr, "%8X -> %8X len: %lu\n", iph->saddr, iph->daddr,
            ntohs(iph->tot_len) + sizeof(struct ethhdr));
  } else if (eth_proto == ETH_P_ARP) {
    fprintf(stderr, "[ARP] %8X -> %8X\n",
            *(uint32_t *)((uint8_t *)pkt_data + 28),
            *(uint32_t *)((uint8_t *)pkt_data + 38));
  } else {
    fprintf(stderr, "unknown eth type\n");
  }
#endif

  if (!dest_port.TxPacket(pkt_data, pkt_len, cur_ts))
    fprintf(stderr, "forward_pkt: dropping packet on port %zu\n", port_id);
}

static void switch_pkt(NetPort &port, size_t iport) {
  const void *pkt_data;
  size_t pkt_len;

#ifdef NETSWITCH_STAT
  d2n_poll_total += 1;
  if (stat_flag) {
    s_d2n_poll_total += 1;
  }
#endif

  enum NetPort::RxPollState poll = port.RxPacket(pkt_data, pkt_len, cur_ts);
  if (poll == NetPort::kRxPollFail) {
    return;
  }

#ifdef NETSWITCH_STAT
  d2n_poll_suc += 1;
  if (stat_flag) {
    s_d2n_poll_suc += 1;
  }
#endif

  if (poll == NetPort::kRxPollSuccess) {
    // Get MAC addresses
    MAC dst((const uint8_t *)pkt_data), src((const uint8_t *)pkt_data + 6);
    // MAC learning

    if (!(src == bcast_addr)) {
      mac_table[src] = iport;
    }

    // L2 forwarding
    auto i = mac_table.find(dst);
    if (i != mac_table.end()) {
      size_t eport = i->second;
      if (eport != iport)
        forward_pkt(pkt_data, pkt_len, eport, iport);
    } else {
      // Broadcast
      struct ethhdr *eth_hdr = (struct ethhdr*)pkt_data;
      struct MemOp *memop = (struct MemOp *)(((const uint8_t *)pkt_data) +42);
      uint64_t phy_addr = 0;

      for (size_t i = 0; i < map_table.size(); i++)
      {
        if (memop->as_id == map_table[i].as_id &&
          memop->addr >= map_table[i].vaddr_start && 
          memop->addr <= map_table[i].vaddr_end){

            // Translate the virtual address to physical address
            phy_addr = map_table[i].phys_start + (memop->addr - map_table[i].vaddr_start);
            memop->addr = phy_addr;

            // modify the destination MAC address
            for (int k = 0; k < ETH_ALEN; k++){
              eth_hdr->h_dest[k] = map_table[i].node_mac.ether_addr_octet[k]; 
            }
            dst = eth_hdr->h_dest;
            auto k = mac_table.find(dst);
            if (k != mac_table.end()) {
              size_t eport = k->second;
              if (eport != iport){
                #ifdef NETSWITCH_DEBUG
                  printf("Forwarding memop to netmem");
                #endif
                forward_pkt(pkt_data, pkt_len, eport, iport);
              }
            }else {
              #ifdef NETSWITCH_DEBUG
                printf("Dest netmem is not in the mac table, broadcast first\n");
              #endif
              for (size_t eport = 0; eport < ports.size(); eport++) {
                if (eport != iport) {
                  // Do not forward to ingress port
                  forward_pkt(pkt_data, pkt_len, eport, iport);
                }
              }
            }
          break;
        }
        if (i == map_table.size()-1)
        {
          fprintf(stderr, "Dest netmem is unavaliable.");
        }
      }
    }
  } else if (poll == NetPort::kRxPollSync) {
#ifdef NETSWITCH_STAT
    d2n_poll_sync += 1;
    if (stat_flag) {
      s_d2n_poll_sync += 1;
    }
#endif
  } else {
    fprintf(stderr, "switch_pkt: unsupported poll result=%u\n", poll);
    abort();
  }
  port.RxDone();
}

int main(int argc, char *argv[]) {
  int c;
  int bad_option = 0;
  int sync_eth = 1;
  pcap_t *pc = nullptr;
  int netmem_idx = 0;
  size_t port_i;
  std::string netmem_name;

  SimbricksNetIfDefaultParams(&netParams);

  // Parse command line argument
  while ((c = getopt(argc, argv, "s:h:uS:E:p:m:")) != -1 && !bad_option) {
    switch (c) {
      case 's': {
        NetPort *port = new NetPort(optarg, sync_eth);
        fprintf(stderr, "Switch connecting to: %s\n", optarg);
        ports.push_back(port);
        break;
      }

      case 'h': {
        NetListenPort *port = new NetListenPort(optarg, sync_eth);
        fprintf(stderr, "Switch listening on: %s\n", optarg);
        ports.push_back(port);
        break;
      }

      case 'u':
        sync_eth = 0;
        break;

      case 'S':
        netParams.sync_interval = strtoull(optarg, NULL, 0) * 1000ULL;
        break;

      case 'E':
        netParams.link_latency = strtoull(optarg, NULL, 0) * 1000ULL;
        break;

      case 'p':
        pc = pcap_open_dead_with_tstamp_precision(DLT_EN10MB, 65535,
                                                  PCAP_TSTAMP_PRECISION_NANO);
        if (pc == nullptr) {
          perror("pcap_open_dead failed");
          return EXIT_FAILURE;
        }

        dumpfile = pcap_dump_open(pc, optarg);
        break;

      case 'm':
        char *token;
        int idx;
        struct table_entry ent;
        

        token = strtok(optarg, ",");
        idx = 0;
        while(token){
          switch (idx){
            case 0:
              ent.as_id = atoi(token);
              break;
            case 1:
              ent.vaddr_start = strtoull(token, NULL, 0);
              break;
            case 2:
              ent.vaddr_end = strtoull(token, NULL, 0);
              break;
            case 3:
              ent.node_mac.ether_addr_64 = strtoull(token, NULL, 16);
              break;
            case 4:
              ent.phys_start = strtoull(token, NULL, 0);
              break;
          }
          idx++;
          
          token = strtok(NULL, ",");
        }
        #ifdef NETSWITCH_DEBUG
          printf("as_id: %lu vaddr_start: %lu  vadd_end: %lu phys_start: %lu\n", ent.as_id, ent.vaddr_start, ent.vaddr_end, ent.phys_start);
          printf("mac_byte: %lx\n", ent.node_mac.ether_addr_64);
        #endif
        map_table.push_back(ent);
        
        // we match this mac address with port number manualy 
        // and statically generate mac table for netmems.

        netmem_name = std::string("netmem") + std::to_string(netmem_idx);
         for (port_i = 0; port_i < ports.size(); port_i++) {
            auto &port = *ports[port_i];
            std::string sockpath = port.path_;
            if (sockpath.find(netmem_name) != std::string::npos){
              uint8_t *temp = (uint8_t *) malloc(6);
              memcpy(temp, (const uint8_t *)ent.node_mac.ether_addr_octet, 6);
              MAC node_mac((const uint8_t *) temp);
              bool existing = false;
              for (auto iter = mac_table.begin(); iter != mac_table.end(); ++iter) {
                if (iter->first == node_mac){
                  existing = true;
                  break;
                }
              }
              if (existing){
                break;
              }else {
                printf("port id for %s is %lu\n", netmem_name.c_str(), port_i);
                mac_table.insert({node_mac,port_i});
                printf("mac_8: %X:%X:%X:%X:%X:%X\n", node_mac.data[0], node_mac.data[1], node_mac.data[2], node_mac.data[3], node_mac.data[4], node_mac.data[5]);
                netmem_idx++;
              }
            }
          }

        
        break;

      default:
        fprintf(stderr, "unknown option %c\n", c);
        bad_option = 1;
        break;
    }
  }

  // for (auto i : map_table){
  //   printf("as_id: %d vaddr_start: %lu  vadd_end: %lu phys_start: %lu\n", i.as_id, i.vaddr_start, i.vaddr_end, i.phys_start);
  //       printf("mac_byte: %lx\n", i.node_mac.ether_addr_64);
  // }
  for (auto& i: mac_table){
    printf("port id: %d: ", i.second);
      printf("mac_8: %X:%X:%X:%X:%X:%X\n", i.first.data[0], i.first.data[1],i.first.data[2],i.first.data[3],i.first.data[4],i.first.data[5]);

  }

  if (ports.empty() || bad_option) {
    fprintf(stderr,
            "Usage: net_switch [-S SYNC-PERIOD] [-E ETH-LATENCY] "
            "-s SOCKET-A [-s SOCKET-B ...]\n");
    return EXIT_FAILURE;
  }

  signal(SIGINT, sigint_handler);
  signal(SIGTERM, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

#ifdef NETSWITCH_STAT
  signal(SIGUSR2, sigusr2_handler);
#endif

  if (!ConnectAll(ports))
    return EXIT_FAILURE;

  printf("start polling\n");
  while (!exiting) {
    // Sync all interfaces
    for (auto port : ports)
      port->Sync(cur_ts);

    // Switch packets
    uint64_t min_ts;
    do {
      min_ts = ULLONG_MAX;
      for (size_t port_i = 0; port_i < ports.size(); port_i++) {
        auto &port = *ports[port_i];
        switch_pkt(port, port_i);
        if (port.IsSync()) {
          uint64_t ts = port.NextTimestamp();
          min_ts = ts < min_ts ? ts : min_ts;
        }
      }
    } while (!exiting && (min_ts <= cur_ts));

    // Update cur_ts
    if (min_ts < ULLONG_MAX) {
      cur_ts = min_ts;
    }
  }

#ifdef NETSWITCH_STAT
  fprintf(stderr, "%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n",
          "d2n_poll_total", d2n_poll_total, "d2n_poll_suc", d2n_poll_suc,
          (double)d2n_poll_suc / d2n_poll_total);
  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "d2n_poll_sync",
          d2n_poll_sync, (double)d2n_poll_sync / d2n_poll_suc);

  fprintf(stderr, "%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n",
          "s_d2n_poll_total", s_d2n_poll_total, "s_d2n_poll_suc",
          s_d2n_poll_suc, (double)s_d2n_poll_suc / s_d2n_poll_total);
  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "s_d2n_poll_sync",
          s_d2n_poll_sync, (double)s_d2n_poll_sync / s_d2n_poll_suc);
#endif

  return 0;
}
