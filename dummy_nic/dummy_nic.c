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

#include "dummy_nic.h"

uint8_t *d2h_queue;
size_t d2h_pos;

uint8_t *h2d_queue;
size_t h2d_pos;


int main(int argc, char *argv[])
{
    int shm_fd, pci_lfd, pci_cfd;
    size_t d2h_off, h2d_off;
    void *shmptr;

    if ((shm_fd = shm_create("/dev/shm/dummy_nic_shm", 32 * 1024 * 1024, &shmptr)) < 0) {
        return EXIT_FAILURE;
    }

    if ((pci_lfd = uxsocket_init("/tmp/cosim-pci")) < 0) {
        return EXIT_FAILURE;
    }

    if ((pci_cfd = accept(pci_lfd, NULL, NULL)) < 0) { 
        perror("accept pci_lfd failed");
        return EXIT_FAILURE;
    }
    printf("connection accepted\n");

    d2h_off = 0;
    h2d_off = (uint64_t) D2H_ELEN * D2H_ENUM;

    d2h_queue = (uint8_t *) shmptr + d2h_off;
    h2d_queue = (uint8_t *) shmptr + h2d_off;

    d2h_pos = h2d_pos = 0;

    struct cosim_pcie_proto_dev_intro di;
    memset(&di, 0, sizeof(di));

    di.d2h_offset = d2h_off;
    di.d2h_elen = D2H_ELEN;
    di.d2h_nentries = D2H_ENUM;

    di.h2d_offset = h2d_off;
    di.h2d_elen = H2D_ELEN;
    di.h2d_nentries = H2D_ENUM;

    di.bars[0].len = 0x1000;
    di.bars[0].flags = COSIM_PCIE_PROTO_BAR_64;

    di.bars[2].len = 128;
    di.bars[2].flags = COSIM_PCIE_PROTO_BAR_IO;

    if (uxsocket_send(pci_cfd, &di, sizeof(di), shm_fd)) {
        return EXIT_FAILURE;
    }
    printf("connection sent\n");


    struct cosim_pcie_proto_host_intro hi;
    if (recv(pci_cfd, &hi, sizeof(hi), 0) != sizeof(hi)) {

        return EXIT_FAILURE;
    }
    printf("host info received\n");

    while (1) {
        poll_h2d();
    }
    close(pci_lfd);

    return 0;
}
