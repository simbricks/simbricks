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

#include <cassert>
#include <climits>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unordered_map>
#include <vector>

extern "C" {
#include <simbricks/netif/netsim.h>
};

static uint64_t sync_period = (500 * 1000ULL);  // 500ns
static uint64_t eth_latency = (500 * 1000ULL);  // 500ns

/* MAC address type */
struct MAC {
  const volatile uint8_t *data;

  MAC(const volatile uint8_t *data) : data(data) {
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

/* Global variables */
static uint64_t cur_ts = 0;
static int exiting = 0;
static const volatile uint8_t bcast[6] = {0xFF};
static const MAC bcast_addr(bcast);
static std::vector<struct netsim_interface> nsifs;
static std::unordered_map<MAC, int> mac_table;

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void forward_pkt(volatile struct SimbricksProtoNetD2NSend *tx,
                        int port) {
  volatile union SimbricksProtoNetN2D *msg_to;
  msg_to = netsim_n2d_alloc(&nsifs[port], cur_ts, eth_latency);
  if (msg_to != NULL) {
    volatile struct SimbricksProtoNetN2DRecv *rx;
    rx = &msg_to->recv;
    rx->len = tx->len;
    rx->port = 0;
    memcpy((void *)rx->data, (void *)tx->data, tx->len);

    // WMB();
    rx->own_type = SIMBRICKS_PROTO_NET_N2D_MSG_RECV |
        SIMBRICKS_PROTO_NET_N2D_OWN_DEV;
  } else {
    fprintf(stderr, "forward_pkt: dropping packet\n");
  }
}

static void switch_pkt(struct netsim_interface *nsif, int iport) {
  volatile union SimbricksProtoNetD2N *msg_from =
      netsim_d2n_poll(nsif, cur_ts);
  if (msg_from == NULL) {
    return;
  }

  uint8_t type = msg_from->dummy.own_type & SIMBRICKS_PROTO_NET_D2N_MSG_MASK;
  if (type == SIMBRICKS_PROTO_NET_D2N_MSG_SEND) {
    volatile struct SimbricksProtoNetD2NSend *tx;
    tx = &msg_from->send;
    // Get MAC addresses
    MAC dst(tx->data), src(tx->data + 6);
    // MAC learning
    if (!(src == bcast_addr)) {
      mac_table[src] = iport;
    }
    // L2 forwarding
    if (mac_table.count(dst) > 0) {
      int eport = mac_table.at(dst);
      forward_pkt(tx, eport);
    } else {
      // Broadcast
      for (int eport = 0; eport < nsifs.size(); eport++) {
        if (eport != iport) {
          // Do not forward to ingress port
          forward_pkt(tx, eport);
        }
      }
    }
  } else if (type == SIMBRICKS_PROTO_NET_D2N_MSG_SYNC) {
  } else {
    fprintf(stderr, "switch_pkt: unsupported type=%u\n", type);
    abort();
  }
  netsim_d2n_done(nsif, msg_from);
}

int main(int argc, char *argv[]) {
  int c;
  int bad_option = 0;
  int sync_mode = SYNC_MODES;

  // Parse command line argument
  while ((c = getopt(argc, argv, "s:S:E:m:")) != -1 && !bad_option) {
    switch (c) {
      case 's': {
        struct netsim_interface nsif;
        int sync = 1;
        if (netsim_init(&nsif, optarg, &sync) != 0) {
          fprintf(stderr, "connecting to %s failed\n", optarg);
          return EXIT_FAILURE;
        }
        nsifs.push_back(nsif);
        break;
      }

      case 'S':
        sync_period = strtoull(optarg, NULL, 0) * 1000ULL;
        break;

      case 'E':
        eth_latency = strtoull(optarg, NULL, 0) * 1000ULL;
        break;

      case 'm':
        sync_mode = strtol(optarg, NULL, 0);
        assert(sync_mode == SYNC_MODES || sync_mode == SYNC_BARRIER);
        break;

      default:
        fprintf(stderr, "unknown option %c\n", c);
        bad_option = 1;
        break;
    }
  }

  if (nsifs.empty() || bad_option) {
    fprintf(stderr,
            "Usage: net_switch [-S SYNC-PERIOD] [-E ETH-LATENCY] "
            "-s SOCKET-A [-s SOCKET-B ...]\n");
    return EXIT_FAILURE;
  }

  signal(SIGINT, sigint_handler);
  signal(SIGTERM, sigint_handler);

  printf("start polling\n");
  while (!exiting) {
    // Sync all interfaces
    for (auto &nsif : nsifs) {
      if (netsim_n2d_sync(&nsif, cur_ts, eth_latency, sync_period, sync_mode) !=
          0) {
        fprintf(stderr, "netsim_n2d_sync failed\n");
        abort();
      }
    }
    netsim_advance_epoch(cur_ts, sync_period, sync_mode);

    // Switch packets
    uint64_t min_ts;
    do {
      min_ts = ULLONG_MAX;
      for (int port = 0; port < nsifs.size(); port++) {
        auto &nsif = nsifs.at(port);
        switch_pkt(&nsif, port);
        if (nsif.sync) {
          uint64_t ts = netsim_d2n_timestamp(&nsif);
          min_ts = ts < min_ts ? ts : min_ts;
        }
      }
    } while (!exiting && (min_ts <= cur_ts));

    // Update cur_ts
    if (min_ts < ULLONG_MAX) {
      cur_ts = netsim_advance_time(min_ts, sync_period, sync_mode);
    }
  }

  return 0;
}
