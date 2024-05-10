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
};

// #define NETSWITCH_DEBUG
#define NETSWITCH_STAT

struct SimbricksBaseIfParams netParams;
static pcap_dumper_t *dumpfile = nullptr;
#define PKT_LEN 1500                                           // byte
static uint64_t bit_rate = 100 * 1000ULL * 1000ULL * 1000ULL;  // 100 Gbps
static uint64_t target_tick = 1 * 1000ULL * 1000ULL * 1000ULL * 1000ULL;  // 1s
static uint64_t last_pkt_sent = 0;
static uint64_t pkt_recv_num = 0;
static uint64_t pkt_recv_byte = 0;
static uint64_t pkt_tx_num = 0;
static uint64_t pkt_tx_byte = 0;
static uint64_t period = (1E12 * 8 * PKT_LEN) / bit_rate;  // per packet
static uint8_t packet[PKT_LEN];

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

struct mac_addr {
  uint8_t addr[6];
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

  struct mac_addr my_mac;
  struct mac_addr dest_mac;

  virtual ~Port() = default;

  virtual bool Connect(const char *path, int sync) = 0;
  virtual bool IsSync() = 0;
  virtual void Sync(uint64_t cur_ts) = 0;
  virtual uint64_t NextTimestamp() = 0;
  virtual enum RxPollState RxPacket(const void *&data, size_t &len,
                                    uint64_t cur_ts) = 0;
  virtual void RxDone() = 0;
  virtual bool TxPacket(const void *data, size_t len, uint64_t cur_ts) = 0;
};

/** Normal network switch port (conneting to a NIC) */
class NetPort : public Port {
 protected:
  struct SimbricksNetIf netifObj_;
  struct SimbricksNetIf *netif_;
  volatile union SimbricksProtoNetMsg *rx_;
  int sync_;

 public:
  NetPort() : netif_(&netifObj_), rx_(nullptr), sync_(0) {
    memset(&netifObj_, 0, sizeof(netifObj_));
    memset(&my_mac, 0, sizeof(my_mac));
    memset(&dest_mac, 0, sizeof(dest_mac));
  }

  NetPort(const NetPort &other)
      : netifObj_(other.netifObj_),
        netif_(&netifObj_),
        rx_(other.rx_),
        sync_(other.sync_) {
  }

  bool Connect(const char *path, int sync) override {
    sync_ = sync;
    return SimbricksNetIfInit(netif_, &netParams, path, &sync_) == 0;
  }

  bool IsSync() override {
    return sync_;
  }

  void Sync(uint64_t cur_ts) override {
    while (SimbricksNetIfOutSync(netif_, cur_ts)) {
    }
  }

  uint64_t NextTimestamp() override {
    return SimbricksNetIfInTimestamp(netif_);
  }

  enum RxPollState RxPacket(const void *&data, size_t &len,
                            uint64_t cur_ts) override {
    assert(rx_ == nullptr);

    rx_ = SimbricksNetIfInPoll(netif_, cur_ts);
    if (!rx_)
      return kRxPollFail;

    uint8_t type = SimbricksNetIfInType(netif_, rx_);
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

  void RxDone() override {
    assert(rx_ != nullptr);

    SimbricksNetIfInDone(netif_, rx_);
    rx_ = nullptr;
  }

  bool TxPacket(const void *data, size_t len, uint64_t cur_ts) override {
    volatile union SimbricksProtoNetMsg *msg_to =
        SimbricksNetIfOutAlloc(netif_, cur_ts);
    if (!msg_to && !sync_) {
      return false;
    } else if (!msg_to && sync_) {
      while (!msg_to)
        msg_to = SimbricksNetIfOutAlloc(netif_, cur_ts);
    }
    volatile struct SimbricksProtoNetMsgPacket *rx;
    rx = &msg_to->packet;
    rx->len = len;
    rx->port = 0;
    memcpy((void *)rx->data, data, len);

    SimbricksNetIfOutSend(netif_, msg_to, SIMBRICKS_PROTO_NET_MSG_PACKET);
    return true;
  }
};

/** Hosting network switch port (connected to another network) */
class NetHostPort : public NetPort {
 protected:
  struct SimbricksNicIf nicif_;

 public:
  NetHostPort() {
    netif_ = &nicif_.net;
    memset(&nicif_, 0, sizeof(nicif_));
  }

  NetHostPort(const NetHostPort &other) : NetPort(other), nicif_(other.nicif_) {
    netif_ = &nicif_.net;
  }

  bool Connect(const char *path, int sync) override {
    sync_ = sync;
    std::string shm_path = path;
    shm_path += "-shm";
    struct SimbricksBaseIfParams params = netParams;
    params.sock_path = path;
    if (!sync)
      params.sync_mode = kSimbricksBaseIfSyncDisabled;
    int ret = SimbricksNicIfInit(&nicif_, shm_path.c_str(), &params, nullptr,
                                 nullptr);
    sync_ = SimbricksBaseIfSyncEnabled(&netif_->base);
    return ret == 0;
  }

  bool IsSync() override {
    return sync_;
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

[[maybe_unused]] static void forward_pkt(const void *pkt_data, size_t pkt_len,
                                         size_t port_id) {
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
  hdr = (struct ethhdr *)pkt_data;
  eth_proto = ntohs(hdr->h_proto);
  iph = (struct iphdr *)(hdr + 1);
  fprintf(stderr, "%20lu: ", cur_ts);
  if (eth_proto == ETH_P_IP) {
    fprintf(stderr, "[ IP] ");

  } else if (eth_proto == ETH_P_ARP) {
    fprintf(stderr, "[ARP] ");
  } else {
    fprintf(stderr, "unkwon eth type\n");
  }

  fprintf(stderr, "%8X -> %8X len: %lu\n ", iph->saddr, iph->daddr,
          iph->tot_len + sizeof(struct ethhdr));
#endif

  if (!dest_port.TxPacket(pkt_data, pkt_len, cur_ts))
    fprintf(stderr, "forward_pkt: dropping packet on port %zu\n", port_id);
}

static void pollq(Port &port, size_t iport) {
  // poll N2D queue
  // send packet
  const void *pkt_data;
  size_t pkt_len;

#ifdef NETSWITCH_STAT
  d2n_poll_total += 1;
  if (stat_flag) {
    s_d2n_poll_total += 1;
  }
#endif

#ifdef NETSWITCH_STAT
  d2n_poll_suc += 1;
  if (stat_flag) {
    s_d2n_poll_suc += 1;
  }
#endif

  enum Port::RxPollState poll = port.RxPacket(pkt_data, pkt_len, cur_ts);
  if (poll == Port::kRxPollFail) {
    return;  // do nothing
  }

  if (poll == Port::kRxPollSuccess) {
    // stat received bytes
    pkt_recv_num++;
    pkt_recv_byte += pkt_len;

    // Get MAC addresses
    // MAC dst((const uint8_t *)pkt_data), src((const uint8_t *)pkt_data + 6);
    // // MAC learning
    // if (!(src == bcast_addr)) {
    //   mac_table[src] = iport;
    // }
    // // L2 forwarding
    // auto i = mac_table.find(dst);
    // if (i != mac_table.end()) {
    //   size_t eport = i->second;
    //   forward_pkt(pkt_data, pkt_len, eport);
    // } else {
    //   // Broadcast
    //   for (size_t eport = 0; eport < ports.size(); eport++) {
    //     if (eport != iport) {
    //       // Do not forward to ingress port
    //       forward_pkt(pkt_data, pkt_len, eport);
    //     }
    //   }
    // }
  } else if (poll == Port::kRxPollSync) {
#ifdef NETSWITCH_STAT
    d2n_poll_sync += 1;
    if (stat_flag) {
      s_d2n_poll_sync += 1;
    }
#endif
  } else {
    fprintf(stderr, "pktgen: unsupported poll result=%u\n", poll);
    abort();
  }
  port.RxDone();
}

static void sendq(Port &port, size_t iport) {
  // then send
  if (port.IsSync()) {
    while ((last_pkt_sent + period) <= cur_ts) {
      port.TxPacket(packet, PKT_LEN, last_pkt_sent + period);
      last_pkt_sent += period;
      pkt_tx_num++;
      pkt_tx_byte += PKT_LEN;
    }
  } else {
    port.TxPacket(packet, PKT_LEN, last_pkt_sent + period);
  }
  // if not sync: send packet
  // else: send packet periodically until allowed time
  // while(allowed_timestamp){ since_last_send + period = to_send_time <=
  // curtick
  //  txpacket(todest)
  // }
}

int main(int argc, char *argv[]) {
  int c;
  int bad_option = 0;
  int sync_eth = 1;
  pcap_t *pc = nullptr;
  int my_num = 0;
  int brate = 10;

  SimbricksNetIfDefaultParams(&netParams);

  // Parse command line argument
  while ((c = getopt(argc, argv, "s:h:uS:E:p:n:b:")) != -1 && !bad_option) {
    switch (c) {
      case 's': {
        NetPort *port = new NetPort;
        fprintf(stderr, "pktgen connecting to: %s\n", optarg);
        if (!port->Connect(optarg, sync_eth)) {
          fprintf(stderr, "connecting to %s failed\n", optarg);
          return EXIT_FAILURE;
        }
        ports.push_back(port);
        break;
      }

      case 'h': {
        NetHostPort *port = new NetHostPort;
        fprintf(stderr, "pktgen listening on: %s\n", optarg);
        if (!port->Connect(optarg, sync_eth)) {
          fprintf(stderr, "listening on %s failed\n", optarg);
          return EXIT_FAILURE;
        }
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
      case 'n':
        my_num = strtol(optarg, NULL, 0);
        fprintf(stderr, "my_num is: %d\n", my_num);
        assert(my_num < 255);
        break;

      case 'b':
        brate = strtol(optarg, NULL, 0);
        fprintf(stderr, "bit rate set to: %d Gbps\n", brate);
        if (brate == 0) {
          period = ULLONG_MAX;
        } else {
          bit_rate = brate * 1000ULL * 1000ULL * 1000ULL;
          period = (1E12 * 8 * PKT_LEN) / bit_rate;  // per packet
        }
        assert(brate < 200);
        break;

      default:
        fprintf(stderr, "unknown option %c\n", c);
        bad_option = 1;
        break;
    }
  }

  if (ports.empty() || bad_option) {
    fprintf(stderr,
            "Usage: pktgen [-S SYNC-PERIOD] [-E ETH-LATENCY] "
            "-s SOCKET-A [-s SOCKET-B ...] [-n my_num] [-b bitrate(GB)]\n");
    return EXIT_FAILURE;
  }

  Port *pkt_port = ports.front();
  pkt_port->my_mac.addr[5] = my_num;
  if (my_num % 2) {  // odd num
    pkt_port->dest_mac.addr[5] = my_num - 1;
  } else {  // even number
    pkt_port->dest_mac.addr[5] = my_num + 1;
  }
  struct mac_addr *mac_tmp = (struct mac_addr *)(&packet[0]);
  mac_tmp->addr[5] = pkt_port->dest_mac.addr[5];  // dest mac
  mac_tmp = (struct mac_addr *)(&packet[6]);
  mac_tmp->addr[5] = pkt_port->my_mac.addr[5];  // source mac

  int kk;
  for (kk = 12; kk < PKT_LEN - 12; kk++) {
    packet[kk] = 0xFF;
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

    // Switch packets
    uint64_t min_ts;
    do {
      min_ts = ULLONG_MAX;
      for (size_t port_i = 0; port_i < ports.size(); port_i++) {
        auto &port = *ports[port_i];
        pollq(port, port_i);
        sendq(port, port_i);
        if (port.IsSync()) {
          uint64_t ts = port.NextTimestamp();
          min_ts = ts < min_ts ? ts : min_ts;
        }
      }
    } while (!exiting && (min_ts <= cur_ts));

    // Update cur_ts
    if (min_ts < ULLONG_MAX) {
      // a bit broken but should probably do
      cur_ts = min_ts;
      if (cur_ts >= target_tick) {
        printf("run to %lu tics\n", cur_ts);
        exiting = 1;
      }
    }
  }

#ifdef NETSWITCH_STAT
  fprintf(stderr, "sent packet: %20lu  [%20lu Byte]\n", pkt_tx_num,
          pkt_tx_byte);
  fprintf(stderr, "recv packet: %20lu  [%20lu Byte]\n", pkt_recv_num,
          pkt_recv_byte);

#endif

  return 0;
}
