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
#include <fcntl.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cassert>
#include <chrono>
#include <climits>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <queue>
#include <set>
#include <string>
#include <vector>

#include <simbricks/base/cxxatomicfix.h>
extern "C" {
#include <simbricks/network/if.h>
};
#include <utils/json.hpp>

//#define DEBUG

using json = nlohmann::json;

typedef long long int ts_t;

static const int log_wait_limit_ms = 10;  // 10ms
static ts_t cur_ts = 0;
static int exiting = 0;
static std::vector<struct SimbricksNetIf> nsifs;
static std::vector<int> tofino_fds;
static std::ifstream log_ifs;
static std::string log_line;
static const int flush_msg_sz = 14;
static char flush_msg[flush_msg_sz] = {0x0};

static void sigint_handler(int dummy) {
  exiting = 1;
}

struct packet_info {
  unsigned int port;
  ts_t latency;
};

struct event {
  ts_t time;
  bool to_switch;
  unsigned int port;
  std::string msg;
};
struct classcomp {
  bool operator()(const struct event &lhs, const struct event &rhs) const {
    return lhs.time > rhs.time;
  }
};
std::priority_queue<struct event, std::vector<struct event>, classcomp>
    event_queue;

static bool get_tofino_log_line(int limit_ms) {
  using std::chrono::system_clock;
  system_clock::time_point start, end;
  char buf[16384];
  start = system_clock::now();

  do {
    log_ifs.clear();
    log_ifs.getline(buf, 16384);
    log_line.append(buf);
    end = system_clock::now();
  } while (!log_ifs.good() &&
           (limit_ms < 0 ||
            std::chrono::duration_cast<std::chrono::milliseconds>(end - start)
                    .count() < limit_ms));
  return log_ifs.good();
}

static void get_egress_pkts(ts_t ingress_ts,
                            std::vector<struct packet_info> &pkts) {
  while (get_tofino_log_line(log_wait_limit_ms)) {
    json j = json::parse(log_line);
    log_line.clear();
    if (j.contains("context")) {
      auto context = j.at("context");
      if (context.at("gress").get<std::string>().compare("egress") == 0 &&
          context.at("component").get<std::string>().compare("port") == 0) {
        unsigned int port = j.at("packet").at("port").get<unsigned int>();
        ts_t latency = j.at("sim_time").get<ts_t>() / 100000000 - ingress_ts;
        struct packet_info info = {port, latency};
        pkts.push_back(info);
      }
    } else if (j.contains("message") &&
               j.at("message").get<std::string>().compare(0, 7, "Ingress") ==
                   0) {
      break;
    }
  }
}

static std::vector<struct packet_info> get_tofino_output() {
  std::vector<struct packet_info> pkts;
  // First, get packet ingress time
  ts_t ingress_ts = -1;
  while (ingress_ts < 0) {
    get_tofino_log_line(-1);
    json j = json::parse(log_line);
    log_line.clear();
    if (j.contains("message") &&
        j.at("message").get<std::string>().compare(0, 7, "Ingress") == 0) {
      ingress_ts = j.at("sim_time").get<ts_t>() / 100000000;
    }
  }
  // Next, get egress time for each port
  get_egress_pkts(ingress_ts, pkts);
  // Send a malformatted message to force log flushing
  send(tofino_fds.at(0), flush_msg, flush_msg_sz, 0);
  get_egress_pkts(ingress_ts, pkts);
  return pkts;
}

static ts_t get_min_peer_time() {
  std::set<uint64_t> peer_times;
  for (auto &nsif : nsifs) {
    peer_times.insert(SimbricksNetIfInTimestamp(&nsif));
  }
  return *peer_times.begin();
}

static void switch_to_dev(int port) {
  static const int BUFFER_SIZE = 2048;
  char buf[BUFFER_SIZE];
  volatile union SimbricksProtoNetMsg *msg_to;
  struct sockaddr_ll addr;
  socklen_t addr_len;
  ssize_t n;

#ifdef DEBUG
  printf("forward packet to peer %u at time %llu\n", port, cur_ts);
#endif

  while ((n = recvfrom(tofino_fds.at(port), buf, BUFFER_SIZE, 0,
                       (struct sockaddr *)&addr, &addr_len)) <= 0 ||
         addr.sll_pkttype == PACKET_OUTGOING) {
    ;
  }

  msg_to = SimbricksNetIfOutAlloc(&nsifs[port], cur_ts);
  if (msg_to != nullptr) {
    volatile struct SimbricksProtoNetMsgPacket *rx;
    rx = &msg_to->packet;
    rx->len = n;
    rx->port = 0;
    memcpy((void *)rx->data, (void *)buf, n);

    SimbricksNetIfOutSend(&nsifs[port], msg_to, SIMBRICKS_PROTO_NET_MSG_PACKET);
  } else {
    fprintf(stderr, "switch_to_dev: dropping packet\n");
  }
}

static void process_event(const struct event &e) {
  if (e.to_switch) {
#ifdef DEBUG
    printf("process to_switch event from peer %u at time %llu\n", e.port,
           e.time);
#endif
    if (send(tofino_fds.at(e.port), e.msg.data(), e.msg.length(), 0) <
        (long int)e.msg.length()) {
      fprintf(stderr, "tofino: failed to forward packet to switch\n");
      abort();
    }
    for (const auto &pkt : get_tofino_output()) {
      if (pkt.port < nsifs.size()) {
        auto &nsif = nsifs.at(pkt.port);
        if (SimbricksBaseIfSyncEnabled(&nsif.base)) {
          struct event de;
          de.time = cur_ts + pkt.latency;
          de.to_switch = false;
          de.port = pkt.port;
          event_queue.push(de);
#ifdef DEBUG
          printf("add to_dev event to peer %u at time %llu to queue\n", de.port,
                 de.time);
#endif
        } else {
          switch_to_dev(pkt.port);
        }
      }
    }
  } else {
    switch_to_dev(e.port);
  }
}

static void recv_from_peer(int port) {
  struct SimbricksNetIf *nsif = &nsifs.at(port);
  volatile union SimbricksProtoNetMsg *msg_from =
      SimbricksNetIfInPoll(nsif, cur_ts);
  if (msg_from == nullptr) {
    return;
  }
  uint8_t type = SimbricksNetIfInType(nsif, msg_from);
  if (type == SIMBRICKS_PROTO_NET_MSG_PACKET) {
    struct event e;
    e.time = msg_from->packet.timestamp;
    e.to_switch = true;
    e.port = port;
    e.msg =
        std::string((const char *)msg_from->packet.data, msg_from->packet.len);
#ifdef DEBUG
    printf("received packet from peer %u at time %llu\n", port, e.time);
#endif
    if (SimbricksBaseIfSyncEnabled(&nsif->base)) {
      event_queue.push(e);
#ifdef DEBUG
      printf("add to_switch event from peer %u at time %llu to queue\n", port,
             e.time);
#endif
    } else {
      process_event(e);
    }
  } else if (type == SIMBRICKS_PROTO_MSG_TYPE_SYNC) {
  } else {
    fprintf(stderr, "tofino: unsupported type=%u\n", type);
    abort();
  }
  SimbricksNetIfInDone(nsif, msg_from);
}

static void process_event_queue() {
  while (!event_queue.empty()) {
    const struct event &e = event_queue.top();
    if (e.time <= cur_ts) {
      process_event(e);
      event_queue.pop();
    } else {
      break;
    }
  }
}

int main(int argc, char *argv[]) {
  int c;
  int bad_option = 0;
  int sync = 1;
  std::string tofino_log;
  struct SimbricksBaseIfParams params;

  SimbricksNetIfDefaultParams(&params);

  // Parse command line argument
  while ((c = getopt(argc, argv, "s:S:E:t:u")) != -1 && !bad_option) {
    switch (c) {
      case 's':
        struct SimbricksNetIf nsif;
        if (SimbricksNetIfInit(&nsif, &params, optarg, &sync) != 0) {
          fprintf(stderr, "connecting to %s failed\n", optarg);
          return EXIT_FAILURE;
        }
        nsifs.push_back(nsif);
        break;

      case 'S':
        params.sync_interval = strtoull(optarg, NULL, 0) * 1000ULL;
        break;

      case 'E':
        params.link_latency = strtoull(optarg, NULL, 0) * 1000ULL;
        break;

      case 't':
        tofino_log = std::string(optarg);
        break;

      case 'u':
        sync = 0;
        break;

      default:
        fprintf(stderr, "unknown option %c\n", c);
        bad_option = 1;
        break;
    }
  }

  if (nsifs.empty() || tofino_log.empty() || bad_option) {
    fprintf(stderr,
            "Usage: tofino [-S SYNC-PERIOD] [-E ETH-LATENCY] "
            "-t TOFINO-LOG-PATH -s SOCKET-A [-s SOCKET-B ...]\n");
    return EXIT_FAILURE;
  }

  signal(SIGINT, sigint_handler);
  signal(SIGTERM, sigint_handler);

  // Open Tofino log file
  log_ifs.open(tofino_log.c_str(), std::ifstream::in);
  if (!log_ifs.good()) {
    fprintf(stderr, "Failed to open tofino log file %s\n", tofino_log.c_str());
    abort();
  }

  // Create sockets for Tofino model interfaces
  for (size_t port = 0; port < nsifs.size(); port++) {
    int fd = socket(PF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (fd == -1) {
      fprintf(stderr, "Failed to create raw socket\n");
      abort();
    }

    char ifname[16];
    sprintf(ifname, "veth%ld", port * 2 + 1);
    struct ifreq ifopts;
    memset(&ifopts, 0, sizeof(ifopts));
    strcpy(ifopts.ifr_name, ifname);
    if (ioctl(fd, SIOCGIFINDEX, &ifopts) < 0) {
      fprintf(stderr, "Failed to set ioctl option SIOCGIFINDEX\n");
      abort();
    }

    int sockopt = 1;
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &sockopt, sizeof(sockopt)) ==
        -1) {
      fprintf(stderr, "Failed to set socket option SO_REUSEADDR");
      abort();
    }

    if (fcntl(fd, F_SETFL, O_NONBLOCK) == -1) {
      fprintf(stderr, "Failed to set socket to non-blocking\n");
      abort();
    }

    struct sockaddr_ll sll;
    bzero(&sll, sizeof(sll));
    sll.sll_family = AF_PACKET;
    sll.sll_ifindex = ifopts.ifr_ifindex;

    if (bind(fd, (struct sockaddr *)&sll, sizeof(sll)) == -1) {
      fprintf(stderr, "Failed to bind socket\n");
      abort();
    }

    tofino_fds.push_back(fd);
  }

  fprintf(stderr, "start polling\n");
  while (!exiting) {
    // Sync all interfaces
    for (auto &nsif : nsifs) {
      if (SimbricksNetIfOutSync(&nsif, cur_ts) != 0) {
        fprintf(stderr, "SimbricksNetIfN2DSync failed\n");
        abort();
      }
    }

    // Switch packets
    ts_t min_ts = 0;
    while (!exiting && min_ts <= cur_ts) {
      for (int port = 0; port < (int)nsifs.size(); port++) {
        recv_from_peer(port);
      }
      min_ts = get_min_peer_time();
      process_event_queue();
    }
    if (min_ts > cur_ts) {
      cur_ts = min_ts;
    }
  }

  for (int fd : tofino_fds) {
    close(fd);
  }

  return 0;
}
