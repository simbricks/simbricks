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

static volatile union cosim_pcie_proto_d2h *d2h_alloc(void)
{
    volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
    if (msg == NULL) {
        fprintf(stderr, "d2h_alloc: no entry available\n");
        abort();
    }
    return msg;
}

static void h2d_read(volatile struct cosim_pcie_proto_h2d_read *read)
{
    volatile union cosim_pcie_proto_d2h *msg;
    volatile struct cosim_pcie_proto_d2h_readcomp *rc;
    uint64_t val;

    msg = d2h_alloc();
    rc = &msg->readcomp;

    val = read->offset + 42;
    printf("read(bar=%u, off=%lu, len=%u) = %lu\n", read->bar, read->offset,
            read->len, val);

    memcpy((void *) rc->data, &val, read->len);
    rc->req_id = read->req_id;

    //WMB();
    rc->own_type = COSIM_PCIE_PROTO_D2H_MSG_READCOMP |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

static void h2d_write(volatile struct cosim_pcie_proto_h2d_write *write)
{
    volatile union cosim_pcie_proto_d2h *msg;
    volatile struct cosim_pcie_proto_d2h_writecomp *wc;
    uint64_t val;

    msg = d2h_alloc();
    wc = &msg->writecomp;

    val = 0;
    memcpy(&val, (void *) write->data, write->len);

    printf("write(bar=%u, off=%lu, len=%u, val=%lu)\n", write->bar,
            write->offset, write->len, val);

    wc->req_id = write->req_id;

    //WMB();
    wc->own_type = COSIM_PCIE_PROTO_D2H_MSG_WRITECOMP |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

void poll_h2d(void)
{
    volatile union cosim_pcie_proto_h2d *msg = nicif_h2d_poll();
    uint8_t type;

    if (msg == NULL)
        return;

    type = msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_MSG_MASK;
    switch (type) {
        case COSIM_PCIE_PROTO_H2D_MSG_READ:
            h2d_read(&msg->read);
            break;

        case COSIM_PCIE_PROTO_H2D_MSG_WRITE:
            h2d_write(&msg->write);
            break;

        default:
            fprintf(stderr, "poll_h2d: unsupported type=%u\n", type);
    }

    nicif_h2d_done(msg);
    nicif_h2d_next();
}

int main(int argc, char *argv[])
{
    int sync = 0;
    struct cosim_pcie_proto_dev_intro di;
    memset(&di, 0, sizeof(di));

    di.bars[0].len = 0x1000;
    di.bars[0].flags = COSIM_PCIE_PROTO_BAR_64;

    di.bars[2].len = 128;
    di.bars[2].flags = COSIM_PCIE_PROTO_BAR_IO;

    di.pci_vendor_id = 0x4321;
    di.pci_device_id = 0x1234;
    di.pci_class = 0x02;
    di.pci_subclass = 0x00;
    di.pci_revision = 0x00;
    di.pci_msi_nvecs = 0x00;

    if (nicsim_init(&di, "/tmp/cosim-pci", &sync, NULL, NULL,
                "/dev/shm/dummy_nic_shm"))
    {
        return EXIT_FAILURE;
    }

    while (1) {
        poll_h2d();
    }

    nicsim_cleanup();
    return 0;
}
