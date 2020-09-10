/*
 * Copyright 2020 Max Planck Institute for Software Systems
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
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/if.h>
#include <linux/if_tun.h>

#include <netsim.h>

#define SYNC_PERIOD (500 * 1000ULL) // 500ns
#define ETH_LATENCY (500 * 1000ULL) // 500ns

static void move_pkt(uint64_t cur_ts, struct netsim_interface *from,
        struct netsim_interface *to)
{
    volatile union cosim_eth_proto_d2n *msg_from = netsim_d2n_poll(from, cur_ts);
    volatile union cosim_eth_proto_n2d *msg_to;
    volatile struct cosim_eth_proto_d2n_send *tx;
    volatile struct cosim_eth_proto_n2d_recv *rx;
    uint8_t type;

    if (msg_from == NULL)
        return;

    type = msg_from->dummy.own_type & COSIM_ETH_PROTO_D2N_MSG_MASK;
    if (type == COSIM_ETH_PROTO_D2N_MSG_SEND) {
        tx = &msg_from->send;

        msg_to = netsim_n2d_alloc(to, cur_ts, ETH_LATENCY);
        if (msg_to != NULL) {
            rx = &msg_to->recv;
            rx->len = tx->len;
            rx->port = 0;
            memcpy((void *) rx->data, (void *) tx->data, tx->len);

            // WMB();
            rx->own_type = COSIM_ETH_PROTO_N2D_MSG_RECV |
                COSIM_ETH_PROTO_N2D_OWN_DEV;
        } else {
            fprintf(stderr, "move_pkt: dropping packet\n");
        }
    } else if (type == COSIM_ETH_PROTO_D2N_MSG_SYNC) {
    } else {
        fprintf(stderr, "move_pkt: unsupported type=%u\n", type);
        abort();
    }

    netsim_d2n_done(from, msg_from);
}

int main(int argc, char *argv[])
{
    struct netsim_interface nsif_a, nsif_b;
    uint64_t cur_ts = 0, ts_a, ts_b;
    int sync_a, sync_b;

    if (argc != 3) {
        fprintf(stderr, "Usage: net_tap SOCKET-A SOCKET-B\n");
        return EXIT_FAILURE;
    }

    sync_a = sync_b = 1;
    if (netsim_init(&nsif_a, argv[1], &sync_a) != 0) {
        return -1;
    }
    if (netsim_init(&nsif_b, argv[2], &sync_b) != 0) {
        return -1;
    }

    printf("start polling\n");
    while (1) {
        if (netsim_n2d_sync(&nsif_a, cur_ts, ETH_LATENCY, SYNC_PERIOD) != 0) {
            fprintf(stderr, "netsim_n2d_sync(nsif_a) failed\n");
            abort();
        }
        if (netsim_n2d_sync(&nsif_b, cur_ts, ETH_LATENCY, SYNC_PERIOD) != 0) {
            fprintf(stderr, "netsim_n2d_sync(nsif_a) failed\n");
            abort();
        }

        do {
            move_pkt(cur_ts, &nsif_a, &nsif_b);
            move_pkt(cur_ts, &nsif_b, &nsif_a);
            ts_a = netsim_d2n_timestamp(&nsif_a);
            ts_b = netsim_d2n_timestamp(&nsif_b);
        } while ((sync_a && ts_a <= cur_ts) ||
                (sync_b && ts_b <= cur_ts));

        if (sync_a && sync_b)
            cur_ts = (ts_a <= ts_b ? ts_a : ts_b);
        else if (sync_a)
            cur_ts = ts_a;
        else if (sync_b)
            cur_ts = ts_b;
    }
    return 0;
}
