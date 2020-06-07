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

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <nicsim.h>

#include "internal.h"

#define D2H_ELEN (4096 + 64)
#define D2H_ENUM 1024

#define H2D_ELEN (4096 + 64)
#define H2D_ENUM 1024


static uint8_t *d2h_queue;
static size_t d2h_pos;

static uint8_t *h2d_queue;
static size_t h2d_pos;

static int pci_cfd = -1;

int nicsim_init(struct cosim_pcie_proto_dev_intro *di,
        const char *uxsocket_path, const char *shm_path)
{
    int shm_fd, pci_lfd;
    size_t d2h_off, h2d_off;
    void *shmptr;

    if ((shm_fd = shm_create(shm_path, 32 * 1024 * 1024, &shmptr)) < 0) {
        return -1;
    }

    if ((pci_lfd = uxsocket_init(uxsocket_path)) < 0) {
        return -1;
    }

    if ((pci_cfd = accept(pci_lfd, NULL, NULL)) < 0) { 
        return -1;
    }
    close(pci_lfd);
    printf("connection accepted\n");

    d2h_off = 0;
    h2d_off = (uint64_t) D2H_ELEN * D2H_ENUM;

    d2h_queue = (uint8_t *) shmptr + d2h_off;
    h2d_queue = (uint8_t *) shmptr + h2d_off;

    d2h_pos = h2d_pos = 0;

    di->d2h_offset = d2h_off;
    di->d2h_elen = D2H_ELEN;
    di->d2h_nentries = D2H_ENUM;

    di->h2d_offset = h2d_off;
    di->h2d_elen = H2D_ELEN;
    di->h2d_nentries = H2D_ENUM;

    if (uxsocket_send(pci_cfd, di, sizeof(*di), shm_fd)) {
        return -1;
    }
    printf("connection sent\n");


    struct cosim_pcie_proto_host_intro hi;
    if (recv(pci_cfd, &hi, sizeof(hi), 0) != sizeof(hi)) {
        return -1;
    }
    printf("host info received\n");

    return 0;
}

void nicsim_cleanup(void)
{
    close(pci_cfd);
}

volatile union cosim_pcie_proto_h2d *nicif_h2d_poll(void)
{
    volatile union cosim_pcie_proto_h2d *msg =
        (volatile union cosim_pcie_proto_h2d *)
        (h2d_queue + h2d_pos * H2D_ELEN);

    /* message not ready */
    if ((msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_OWN_MASK) !=
            COSIM_PCIE_PROTO_H2D_OWN_DEV)
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

volatile union cosim_pcie_proto_d2h *nicsim_d2h_alloc(void)
{
    volatile union cosim_pcie_proto_d2h *msg =
        (volatile union cosim_pcie_proto_d2h *)
        (d2h_queue + d2h_pos * D2H_ELEN);

    if ((msg->dummy.own_type & COSIM_PCIE_PROTO_D2H_OWN_MASK) !=
            COSIM_PCIE_PROTO_D2H_OWN_DEV)
    {
        return NULL;
    }

    d2h_pos = (d2h_pos + 1) % D2H_ENUM;
    return msg;
}

