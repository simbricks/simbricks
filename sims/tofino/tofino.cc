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

#include <csignal>
#include <cstdio>
#include <cstring>
#include <climits>
#include <cassert>
#include <cstdlib>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <net/ethernet.h>
#include <linux/if_packet.h>
#include <vector>

extern "C" {
#include <simbricks/netif/netif.h>
#include <simbricks/proto/base.h>
};

static uint64_t sync_period = (500 * 1000ULL);
static uint64_t eth_latency = (500 * 1000ULL);  // 500ns
static uint64_t cur_ts = 0;
static int exiting = 0;
static std::vector<struct SimbricksNetIf> nsifs;
static std::vector<int> tofino_fds;

static void sigint_handler(int dummy) {
    exiting = 1;
}

static void dev_to_switch(struct SimbricksNetIf *nsif, size_t port) {
    volatile union SimbricksProtoNetD2N *msg_from =
        SimbricksNetIfD2NPoll(nsif, cur_ts);
    if (msg_from == nullptr) {
        return;
    }
    uint8_t type = msg_from->dummy.own_type & SIMBRICKS_PROTO_NET_D2N_MSG_MASK;
    if (type == SIMBRICKS_PROTO_NET_D2N_MSG_SEND) {
        volatile struct SimbricksProtoNetD2NSend *tx;
        tx = &msg_from->send;
        if (send(tofino_fds.at(port), (const void *)tx->data, tx->len, 0) < tx->len) {
            fprintf(stderr, "tofino: failed to forward packet to switch\n");
            abort();
        }
    } else if (type == SIMBRICKS_PROTO_NET_D2N_MSG_SYNC) {
    } else {
        fprintf(stderr, "tofino: unsupported type=%u\n", type);
        abort();
    }
    SimbricksNetIfD2NDone(nsif, msg_from);
}

static void switch_to_dev(size_t port) {
    static const int BUFFER_SIZE = 2048;
    char buf[BUFFER_SIZE];
    volatile union SimbricksProtoNetN2D *msg_to;
    struct sockaddr_ll addr;
    socklen_t addr_len;

    ssize_t n = recvfrom(tofino_fds.at(port), buf, BUFFER_SIZE, 0,
            (struct sockaddr*)&addr, &addr_len);
    if (n <= 0 || addr.sll_pkttype == PACKET_OUTGOING) {
        return;
    }

    msg_to = SimbricksNetIfN2DAlloc(&nsifs[port], cur_ts, eth_latency);
    if (msg_to != NULL) {
        volatile struct SimbricksProtoNetN2DRecv *rx;
        rx = &msg_to->recv;
        rx->len = n;
        rx->port = 0;
        memcpy((void *)rx->data, (void *)buf, n);

        // WMB();
        rx->own_type =
            SIMBRICKS_PROTO_NET_N2D_MSG_RECV | SIMBRICKS_PROTO_NET_N2D_OWN_DEV;
    } else {
        fprintf(stderr, "switch_to_dev: dropping packet\n");
    }
}

int main(int argc, char *argv[]) {
    int c;
    int bad_option = 0;
    int sync_mode = SIMBRICKS_PROTO_SYNC_SIMBRICKS;
    int sync = 1;
    struct SimbricksNetIf nsif;

    // Parse command line argument
    while ((c = getopt(argc, argv, "s:S:E:m:")) != -1 && !bad_option) {
        switch (c) {
            case 's':
                if (SimbricksNetIfInit(&nsif, optarg, &sync) != 0) {
                    fprintf(stderr, "connecting to %s failed\n", optarg);
                    return EXIT_FAILURE;
                }
                nsifs.push_back(nsif);
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

            default:
                fprintf(stderr, "unknown option %c\n", c);
                bad_option = 1;
                break;
        }
    }

    if (nsifs.empty() || bad_option) {
        fprintf(stderr,
                "Usage: tofino [-S SYNC-PERIOD] [-E ETH-LATENCY] "
                "-s SOCKET-A [-s SOCKET-B ...]\n");
        return EXIT_FAILURE;
    }

    signal(SIGINT, sigint_handler);
    signal(SIGTERM, sigint_handler);

    // Create sockets for Tofino model interfaces
    for (size_t port = 0; port < nsifs.size(); port++) {
        int fd = socket(PF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
        if (fd == -1) {
            fprintf(stderr, "Failed to create raw socket\n");
            abort();
        }

        char ifname[16];
        sprintf(ifname, "veth%ld", port*2+1);
        struct ifreq ifopts;
        memset(&ifopts, 0, sizeof(ifopts));
        strcpy(ifopts.ifr_name, ifname);
        if (ioctl(fd, SIOCGIFINDEX, &ifopts) < 0) {
            fprintf(stderr, "Failed to set ioctl option SIOCGIFINDEX\n");
            abort();
        }

        int sockopt = 1;
        if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &sockopt, sizeof(sockopt)) == -1) {
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

    printf("start polling\n");
    while (!exiting) {
        // Sync all interfaces
        for (auto &nsif : nsifs) {
            if (SimbricksNetIfN2DSync(&nsif, cur_ts, eth_latency, sync_period,
                        sync_mode) != 0) {
                fprintf(stderr, "SimbricksNetIfN2DSync failed\n");
                abort();
            }
        }
        SimbricksNetIfAdvanceEpoch(cur_ts, sync_period, sync_mode);

        // Switch packets
        uint64_t min_ts;
        do {
            min_ts = ULLONG_MAX;
            for (size_t port = 0; port < nsifs.size(); port++) {
                auto &nsif = nsifs.at(port);
                dev_to_switch(&nsif, port);
                if (nsif.sync) {
                    uint64_t ts = SimbricksNetIfD2NTimestamp(&nsif);
                    min_ts = ts < min_ts ? ts : min_ts;
                }
            }
            for (size_t port = 0; port < nsifs.size(); port++) {
                switch_to_dev(port);
            }
        } while (!exiting && (min_ts <= cur_ts));

        // Update cur_ts
        if (min_ts < ULLONG_MAX) {
            cur_ts = SimbricksNetIfAdvanceTime(min_ts, sync_period, sync_mode);
        }
    }

    for (int fd : tofino_fds) {
        close(fd);
    }

    return 0;
}
