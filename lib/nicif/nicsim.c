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

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <poll.h>
#include <unistd.h>

#include <nicsim.h>

#include "internal.h"

#define D2H_ELEN (9024 + 64)
#define D2H_ENUM 1024

#define H2D_ELEN (9024 + 64)
#define H2D_ENUM 1024

#define D2N_ELEN (9024 + 64)
#define D2N_ENUM 8192

#define N2D_ELEN (9024 + 64)
#define N2D_ENUM 8192


static uint8_t *d2h_queue;
static size_t d2h_pos;
static size_t d2h_off; /* offset in shm region */

static uint8_t *h2d_queue;
static size_t h2d_pos;
static size_t h2d_off; /* offset in shm region */

static uint8_t *d2n_queue;
static size_t d2n_pos;
static size_t d2n_off; /* offset in shm region */

static uint8_t *n2d_queue;
static size_t n2d_pos;
static size_t n2d_off; /* offset in shm region */

static uint64_t pci_last_rx_time = 0;
static uint64_t pci_last_tx_time = 0;
static uint64_t eth_last_rx_time = 0;
static uint64_t eth_last_tx_time = 0;

static uint64_t current_epoch = 0;

static int shm_fd = -1;
static int pci_cfd = -1;
static int eth_cfd = -1;

static int accept_pci(struct cosim_pcie_proto_dev_intro *di, int pci_lfd,
        int *sync_pci)
{
    if ((pci_cfd = accept(pci_lfd, NULL, NULL)) < 0) {
        return -1;
    }
    close(pci_lfd);
    printf("pci connection accepted\n");

    di->d2h_offset = d2h_off;
    di->d2h_elen = D2H_ELEN;
    di->d2h_nentries = D2H_ENUM;

    di->h2d_offset = h2d_off;
    di->h2d_elen = H2D_ELEN;
    di->h2d_nentries = H2D_ENUM;

    if (*sync_pci)
        di->flags |= COSIM_PCIE_PROTO_FLAGS_DI_SYNC;
    else
        di->flags &= ~((uint64_t) COSIM_PCIE_PROTO_FLAGS_DI_SYNC);

    if (uxsocket_send(pci_cfd, di, sizeof(*di), shm_fd)) {
        return -1;
    }
    printf("pci intro sent\n");
    return 0;
}

static int accept_eth(int eth_lfd, int *sync_eth)
{
    struct cosim_eth_proto_dev_intro di;

    if ((eth_cfd = accept(eth_lfd, NULL, NULL)) < 0) {
        return -1;
    }
    close(eth_lfd);
    printf("eth connection accepted\n");

    memset(&di, 0, sizeof(di));
    di.flags = 0;
    if (*sync_eth)
        di.flags |= COSIM_ETH_PROTO_FLAGS_DI_SYNC;

    di.d2n_offset = d2n_off;
    di.d2n_elen = D2N_ELEN;
    di.d2n_nentries = D2N_ENUM;

    di.n2d_offset = n2d_off;
    di.n2d_elen = N2D_ELEN;
    di.n2d_nentries = N2D_ENUM;

    if (uxsocket_send(eth_cfd, &di, sizeof(di), shm_fd)) {
        return -1;
    }
    printf("eth intro sent\n");
    return 0;
}

static int accept_conns(struct cosim_pcie_proto_dev_intro *di,
        int pci_lfd, int *sync_pci, int eth_lfd, int *sync_eth)
{
    struct pollfd pfds[2];
    int await_pci = pci_lfd != -1;
    int await_eth = eth_lfd != -1;
    int ret;

    while (await_pci || await_eth) {
        if (await_pci && await_eth) {
            /* we're waiting on both fds */
            pfds[0].fd = pci_lfd;
            pfds[1].fd = eth_lfd;
            pfds[0].events = pfds[1].events = POLLIN;
            pfds[0].revents = pfds[1].revents = 0;

            ret = poll(pfds, 2, -1);
            if (ret < 0) {
                perror("poll failed");
                return -1;
            }

            if (pfds[0].revents) {
                if (accept_pci(di, pci_lfd, sync_pci) != 0)
                    return -1;
                await_pci = 0;
            }
            if (pfds[1].revents) {
                if (accept_eth(eth_lfd, sync_eth) != 0)
                    return -1;
                await_eth = 0;
            }
        } else if (await_pci) {
            /* waiting just on pci */
            if (accept_pci(di, pci_lfd, sync_pci) != 0)
                return -1;
            await_pci = 0;
        } else {
            /* waiting just on ethernet */
            if (accept_eth(eth_lfd, sync_eth) != 0)
                return -1;
            await_eth = 0;
        }
    }

    return 0;
}

int nicsim_init(struct nicsim_params *params,
        struct cosim_pcie_proto_dev_intro *di)
{
    int pci_lfd = -1, eth_lfd = -1;
    void *shmptr;
    size_t shm_size;

    /* ready in memory queues */
    shm_size = (uint64_t) D2H_ELEN * D2H_ENUM +
        (uint64_t) H2D_ELEN * H2D_ENUM +
        (uint64_t) D2N_ELEN * D2N_ENUM +
        (uint64_t) N2D_ELEN * N2D_ENUM;
    if ((shm_fd = shm_create(params->shm_path, shm_size, &shmptr))
            < 0)
    {

        return -1;
    }

    d2h_off = 0;
    h2d_off = d2h_off + (uint64_t) D2H_ELEN * D2H_ENUM;
    d2n_off = h2d_off + (uint64_t) H2D_ELEN * H2D_ENUM;
    n2d_off = d2n_off + (uint64_t) D2N_ELEN * D2N_ENUM;

    d2h_queue = (uint8_t *) shmptr + d2h_off;
    h2d_queue = (uint8_t *) shmptr + h2d_off;
    d2n_queue = (uint8_t *) shmptr + d2n_off;
    n2d_queue = (uint8_t *) shmptr + n2d_off;

    d2h_pos = h2d_pos = d2n_pos = n2d_pos = 0;

    /* get listening sockets ready */
    if (params->pci_socket_path != NULL) {
        if ((pci_lfd = uxsocket_init(params->pci_socket_path)) < 0) {
            return -1;
        }
    }
    if (params->eth_socket_path != NULL) {
        if ((eth_lfd = uxsocket_init(params->eth_socket_path)) < 0) {
            return -1;
        }
    }

    /* accept connection fds */
    if (accept_conns(di, pci_lfd, &params->sync_pci, eth_lfd,
                &params->sync_eth) != 0)
    {
        return -1;
    }

    /* receive introductions from other end */
    if (params->pci_socket_path != NULL) {
        struct cosim_pcie_proto_host_intro hi;
        if (recv(pci_cfd, &hi, sizeof(hi), 0) != sizeof(hi)) {
            return -1;
        }
        if ((hi.flags & COSIM_PCIE_PROTO_FLAGS_HI_SYNC) == 0)
            params->sync_pci = 0;
        printf("pci host info received\n");
    }
    if (params->eth_socket_path != NULL) {
        struct cosim_eth_proto_net_intro ni;
        if (recv(eth_cfd, &ni, sizeof(ni), 0) != sizeof(ni)) {
            return -1;
        }
        if ((ni.flags & COSIM_ETH_PROTO_FLAGS_NI_SYNC) == 0)
            params->sync_eth = 0;
        printf("eth net info received\n");
    }

    return 0;
}

void nicsim_cleanup(void)
{
    close(pci_cfd);
    close(eth_cfd);
}

/******************************************************************************/
/* Sync */

int nicsim_sync(struct nicsim_params *params, uint64_t timestamp)
{
    int ret = 0;
    volatile union cosim_pcie_proto_d2h *d2h;
    volatile union cosim_eth_proto_d2n *d2n;

    /* sync PCI if necessary */
    if (params->sync_pci) {
        int sync;
        switch (params->sync_mode) {
        case SYNC_MODES:
            sync = pci_last_tx_time == 0 ||
                timestamp - pci_last_tx_time >= params->sync_delay;
            break;
        case SYNC_BARRIER:
            sync = current_epoch == 0 ||
                timestamp - current_epoch >= params->sync_delay;
            break;
        default:
            fprintf(stderr, "unsupported sync mode=%u\n", params->sync_mode);
            return ret;
        }

        if (sync)
        {
            d2h = nicsim_d2h_alloc(params, timestamp);
            if (d2h == NULL) {
                ret = -1;
            } else {
                d2h->sync.own_type = COSIM_PCIE_PROTO_D2H_MSG_SYNC |
                    COSIM_PCIE_PROTO_D2H_OWN_HOST;
            }
        }
    }

    /* sync Ethernet if necessary */
    if (params->sync_eth) {
        int sync;
        switch (params->sync_mode) {
        case SYNC_MODES:
            sync = eth_last_tx_time == 0 ||
                timestamp - eth_last_tx_time >= params->sync_delay;
            break;
        case SYNC_BARRIER:
            sync = current_epoch == 0 ||
                timestamp - current_epoch >= params->sync_delay;
            break;
        default:
            fprintf(stderr, "unsupported sync mode=%u\n", params->sync_mode);
            return ret;
        }

        if (sync)
        {
            d2n = nicsim_d2n_alloc(params, timestamp);
            if (d2n == NULL) {
                ret = -1;
            } else {
                d2n->sync.own_type = COSIM_ETH_PROTO_D2N_MSG_SYNC |
                    COSIM_ETH_PROTO_D2N_OWN_NET;
            }
        }
    }

    return ret;
}

void nicsim_advance_epoch(struct nicsim_params *params, uint64_t timestamp)
{
    if (params->sync_mode == SYNC_BARRIER) {
        if ((params->sync_pci || params->sync_eth) &&
                timestamp - current_epoch >= params->sync_delay) {
            current_epoch = timestamp;
        }
    }
}

uint64_t nicsim_advance_time(struct nicsim_params *params, uint64_t timestamp)
{
    switch (params->sync_mode) {
    case SYNC_MODES:
        return timestamp;
    case SYNC_BARRIER:
        return timestamp < current_epoch + params->sync_delay ?
            timestamp : current_epoch + params->sync_delay;
    default:
        fprintf(stderr, "unsupported sync mode=%u\n", params->sync_mode);
        return timestamp;
    }
}

uint64_t nicsim_next_timestamp(struct nicsim_params *params)
{
    if (params->sync_pci && params->sync_eth) {
        return (pci_last_rx_time <= eth_last_rx_time ? pci_last_rx_time :
                eth_last_rx_time);
    } else if (params->sync_pci) {
        return pci_last_rx_time;
    } else if (params->sync_eth) {
        return eth_last_rx_time;
    } else {
        return 0;
    }
}

/******************************************************************************/
/* PCI */

volatile union cosim_pcie_proto_h2d *nicif_h2d_poll(
        struct nicsim_params *params, uint64_t timestamp)
{
    volatile union cosim_pcie_proto_h2d *msg =
        (volatile union cosim_pcie_proto_h2d *)
        (h2d_queue + h2d_pos * H2D_ELEN);

    /* message not ready */
    if ((msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_OWN_MASK) !=
            COSIM_PCIE_PROTO_H2D_OWN_DEV)
        return NULL;

    /* if in sync mode, wait till message is ready */
    pci_last_rx_time = msg->dummy.timestamp;
    if (params->sync_pci && pci_last_rx_time > timestamp)
        return NULL;

    return msg;
}

void nicif_h2d_done(volatile union cosim_pcie_proto_h2d *msg)
{
    msg->dummy.own_type = (msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_MSG_MASK)
        | COSIM_PCIE_PROTO_H2D_OWN_HOST;
}

void nicif_h2d_next(void)
{
    h2d_pos = (h2d_pos + 1) % H2D_ENUM;
}

volatile union cosim_pcie_proto_d2h *nicsim_d2h_alloc(
        struct nicsim_params *params, uint64_t timestamp)
{
    volatile union cosim_pcie_proto_d2h *msg =
        (volatile union cosim_pcie_proto_d2h *)
        (d2h_queue + d2h_pos * D2H_ELEN);

    if ((msg->dummy.own_type & COSIM_PCIE_PROTO_D2H_OWN_MASK) !=
            COSIM_PCIE_PROTO_D2H_OWN_DEV)
    {
        return NULL;
    }

    msg->dummy.timestamp = timestamp + params->pci_latency;
    pci_last_tx_time = timestamp;

    d2h_pos = (d2h_pos + 1) % D2H_ENUM;
    return msg;
}

/******************************************************************************/
/* Ethernet */

volatile union cosim_eth_proto_n2d *nicif_n2d_poll(
        struct nicsim_params *params, uint64_t timestamp)
{
    volatile union cosim_eth_proto_n2d *msg =
        (volatile union cosim_eth_proto_n2d *)
        (n2d_queue + n2d_pos * N2D_ELEN);

    /* message not ready */
    if ((msg->dummy.own_type & COSIM_ETH_PROTO_N2D_OWN_MASK) !=
            COSIM_ETH_PROTO_N2D_OWN_DEV)
        return NULL;

    /* if in sync mode, wait till message is ready */
    eth_last_rx_time = msg->dummy.timestamp;
    if (params->sync_eth && eth_last_rx_time > timestamp)
        return NULL;

    return msg;
}

void nicif_n2d_done(volatile union cosim_eth_proto_n2d *msg)
{
    msg->dummy.own_type = (msg->dummy.own_type & COSIM_ETH_PROTO_N2D_MSG_MASK)
        | COSIM_ETH_PROTO_N2D_OWN_NET;
}

void nicif_n2d_next(void)
{
    n2d_pos = (n2d_pos + 1) % N2D_ENUM;
}

volatile union cosim_eth_proto_d2n *nicsim_d2n_alloc(
        struct nicsim_params *params, uint64_t timestamp)
{
    volatile union cosim_eth_proto_d2n *msg =
        (volatile union cosim_eth_proto_d2n *)
        (d2n_queue + d2n_pos * D2N_ELEN);

    if ((msg->dummy.own_type & COSIM_ETH_PROTO_D2N_OWN_MASK) !=
            COSIM_ETH_PROTO_D2N_OWN_DEV)
    {
        return NULL;
    }

    msg->dummy.timestamp = timestamp + params->eth_latency;
    eth_last_tx_time = timestamp;

    d2n_pos = (d2n_pos + 1) % D2N_ENUM;
    return msg;
}
