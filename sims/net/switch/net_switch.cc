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

#include <unistd.h>
#include <pcap/pcap.h>
#include <linux/ip.h>
#include <linux/if_ether.h>
#include <arpa/inet.h>

#include <cassert>
#include <climits>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unordered_map>
#include <vector>

extern "C" {
#include <simbricks/netif/netif.h>
#include <simbricks/proto/base.h>
};

//#define NETSWITCH_DEBUG
#define NETSWITCH_STAT

static uint64_t sync_period = (500 * 1000ULL);  // 500ns
static uint64_t eth_latency = (500 * 1000ULL);  // 500ns
static int sync_mode = SIMBRICKS_PROTO_SYNC_SIMBRICKS;
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

/** Abstract base switch port */
class Port {
 public:
  enum RxPollState {
    kRxPollSuccess = 0,
    kRxPollFail = 1,
    kRxPollSync = 2,
  };

  virtual ~Port() = default;

  virtual bool Connect(const char *path, int sync) = 0;
  virtual bool IsSync() = 0;
  virtual void Sync(uint64_t cur_ts) = 0;
  virtual void AdvanceEpoch(uint64_t cur_ts) = 0;
  virtual uint64_t NextTimestamp() = 0;
  virtual enum RxPollState RxPacket(
      const void *& data, size_t &len, uint64_t cur_ts) = 0;
  virtual void RxDone() = 0;
  virtual bool TxPacket(const void *data, size_t len, uint64_t cur_ts) = 0;
};

/** Normal network switch port (conneting to a NIC) */
class NetPort : public Port {
 protected:
  struct SimbricksNetIf netif_;
  volatile union SimbricksProtoNetD2N *rx_;
  int sync_;

 public:
  NetPort() : rx_(nullptr), sync_(0) {
    memset(&netif_, 0, sizeof(netif_));
  }

  NetPort(const NetPort &other) : netif_(other.netif_), rx_(other.rx_),
      sync_(other.sync_) {}

  virtual bool Connect(const char *path, int sync) override {
    sync_ = sync;
    return SimbricksNetIfInit(&netif_, path, &sync_) == 0;
  }

  virtual bool IsSync() override {
    return sync_;
  }

  virtual void Sync(uint64_t cur_ts) override {
    if (SimbricksNetIfN2DSync(&netif_, cur_ts, eth_latency, sync_period,
                              sync_mode) != 0) {
      fprintf(stderr, "SimbricksNetIfN2DSync failed\n");
      abort();
    }
  }

  virtual void AdvanceEpoch(uint64_t cur_ts) override {
    SimbricksNetIfAdvanceEpoch(cur_ts, sync_period, sync_mode);
  }

  virtual uint64_t NextTimestamp() override {
    return SimbricksNetIfD2NTimestamp(&netif_);
  }

  virtual enum RxPollState RxPacket(
      const void *& data, size_t &len, uint64_t cur_ts) override {
    assert(rx_ == nullptr);

    rx_ = SimbricksNetIfD2NPoll(&netif_, cur_ts);
    if (!rx_)
      return kRxPollFail;

    uint8_t type = rx_->dummy.own_type & SIMBRICKS_PROTO_NET_D2N_MSG_MASK;
    if (type == SIMBRICKS_PROTO_NET_D2N_MSG_SEND) {
      data = (const void *)rx_->send.data;
      len = rx_->send.len;
      return kRxPollSuccess;
    } else if (type == SIMBRICKS_PROTO_NET_D2N_MSG_SYNC) {
      return kRxPollSync;
    } else {
      fprintf(stderr, "switch_pkt: unsupported type=%u\n", type);
      abort();
    }
  }

  virtual void RxDone() override {
    assert(rx_ != nullptr);

    SimbricksNetIfD2NDone(&netif_, rx_);
    rx_ = nullptr;
  }

  virtual bool TxPacket(
      const void *data, size_t len, uint64_t cur_ts) override {
    volatile union SimbricksProtoNetN2D *msg_to =
      SimbricksNetIfN2DAlloc(&netif_, cur_ts, eth_latency);
    if (!msg_to)
      return false;

    volatile struct SimbricksProtoNetN2DRecv *rx;
    rx = &msg_to->recv;
    rx->len = len;
    rx->port = 0;
    memcpy((void *)rx->data, data, len);

    // WMB();
    rx->own_type =
        SIMBRICKS_PROTO_NET_N2D_MSG_RECV | SIMBRICKS_PROTO_NET_N2D_OWN_DEV;
    return true;
  }
};

/* Global variables */
static uint64_t cur_ts = 0;
static int exiting = 0;
static const uint8_t bcast[6] = {0xFF};
static const MAC bcast_addr(bcast);
static std::vector<Port *> ports;
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

static void forward_pkt(const void *pkt_data, size_t pkt_len, size_t port_id) {
  struct pcap_pkthdr ph;
  Port &dest_port = *ports[port_id];

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
  hdr = (struct ethhdr*)pkt_data;
  eth_proto = ntohs(hdr->h_proto);
  iph = (struct iphdr *)(hdr + 1);
  fprintf(stderr, "%20lu: ", cur_ts);
  if (eth_proto == ETH_P_IP){
    fprintf(stderr, "[ IP] ");
    
  } 
  else if(eth_proto == ETH_P_ARP){
    fprintf(stderr, "[ARP] ");
  } 
  else{
    fprintf(stderr, "unkwon eth type\n");
  }

  fprintf(stderr, "%8X -> %8X len: %lu\n ", iph->saddr, iph->daddr, iph->tot_len + sizeof(struct ethhdr));
#endif

  if (!dest_port.TxPacket(pkt_data, pkt_len, cur_ts))
    fprintf(stderr, "forward_pkt: dropping packet on port %zu\n", port_id);
}

static void switch_pkt(Port &port, size_t iport) {
  const void *pkt_data;
  size_t pkt_len;

#ifdef NETSWITCH_STAT
  d2n_poll_total += 1;
  if (stat_flag){
    s_d2n_poll_total += 1;
  }
#endif

  enum Port::RxPollState poll = port.RxPacket(pkt_data, pkt_len, cur_ts);
  if (poll == Port::kRxPollFail) {
    return;
  }

#ifdef NETSWITCH_STAT
  d2n_poll_suc += 1;
  if (stat_flag){
    s_d2n_poll_suc += 1;
  }
#endif

  if (poll == Port::kRxPollSuccess) {
    // Get MAC addresses
    MAC dst((const uint8_t *)pkt_data), src((const uint8_t *)pkt_data + 6);
    // MAC learning
    if (!(src == bcast_addr)) {
      mac_table[src] = iport;
    }
    // L2 forwarding
    if (mac_table.count(dst) > 0) {
      size_t eport = mac_table.at(dst);
      forward_pkt(pkt_data, pkt_len, eport);
    } else {
      // Broadcast
      for (size_t eport = 0; eport < ports.size(); eport++) {
        if (eport != iport) {
          // Do not forward to ingress port
          forward_pkt(pkt_data, pkt_len, eport);
        }
      }
    }
  } else if (poll == Port::kRxPollSync) {
#ifdef NETSWITCH_STAT
    d2n_poll_sync += 1;
    if (stat_flag){
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

  // Parse command line argument
  while ((c = getopt(argc, argv, "s:uS:E:m:p:")) != -1 && !bad_option) {
    switch (c) {
      case 's': {
        NetPort *port = new NetPort;
        fprintf(stderr, "Switch connecting to: %s\n", optarg);
        if (!port->Connect(optarg, sync_eth)) {
          fprintf(stderr, "connecting to %s failed\n", optarg);
          return EXIT_FAILURE;
        }
        ports.push_back(port);
        break;
      }

      case 'u':
        sync_eth = 0;
        break;

      case 'S':
        sync_period = strtoull(optarg, NULL, 0) * 1000ULL;
        break;

      case 'E':
        eth_latency = strtoull(optarg, NULL, 0) * 1000ULL;
        break;

      case 'm':
        sync_mode = strtol(optarg, NULL, 0);
        assert(sync_mode == SIMBRICKS_PROTO_SYNC_SIMBRICKS ||
               sync_mode == SIMBRICKS_PROTO_SYNC_BARRIER);
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

      default:
        fprintf(stderr, "unknown option %c\n", c);
        bad_option = 1;
        break;
    }
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


  printf("start polling\n");
  while (!exiting) {
    // Sync all interfaces
    for (auto port : ports)
      port->Sync(cur_ts);
    for (auto port : ports)
      port->AdvanceEpoch(cur_ts);

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
      // a bit broken but should probably do
      cur_ts = SimbricksNetIfAdvanceTime(min_ts, sync_period, sync_mode);
    }
  }

#ifdef NETSWITCH_STAT
  fprintf(stderr, "%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n",
          "d2n_poll_total", d2n_poll_total, "d2n_poll_suc", d2n_poll_suc,
          (double)d2n_poll_suc / d2n_poll_total);
  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "d2n_poll_sync",
          d2n_poll_sync, (double)d2n_poll_sync / d2n_poll_suc);

  fprintf(stderr, "%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n",
          "s_d2n_poll_total", s_d2n_poll_total, "s_d2n_poll_suc", s_d2n_poll_suc,
          (double)s_d2n_poll_suc / s_d2n_poll_total);
  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "s_d2n_poll_sync",
          s_d2n_poll_sync, (double)s_d2n_poll_sync / s_d2n_poll_suc);
#endif

  return 0;
}
