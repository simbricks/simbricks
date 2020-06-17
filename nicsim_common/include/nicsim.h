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

#ifndef COSIM_NICSIM_H_
#define COSIM_NICSIM_H_

#include <cosim_pcie_proto.h>
#include <cosim_eth_proto.h>

struct nicsim_params {
    const char *pci_socket_path;
    const char *eth_socket_path;
    const char *shm_path;

    uint64_t pci_latency;
    uint64_t eth_latency;
    uint64_t sync_delay;

    int sync_pci;
    int sync_eth;
};

int nicsim_init(struct nicsim_params *params,
        struct cosim_pcie_proto_dev_intro *di);
void nicsim_cleanup(void);

int nicsim_sync(struct nicsim_params *params, uint64_t timestamp);
uint64_t netsim_next_timestamp(struct nicsim_params *params);

volatile union cosim_pcie_proto_h2d *nicif_h2d_poll(
        struct nicsim_params *params, uint64_t timestamp);
void nicif_h2d_done(volatile union cosim_pcie_proto_h2d *msg);
void nicif_h2d_next(void);

volatile union cosim_pcie_proto_d2h *nicsim_d2h_alloc(
        struct nicsim_params *params, uint64_t timestamp);


volatile union cosim_eth_proto_n2d *nicif_n2d_poll(
        struct nicsim_params *params, uint64_t timestamp);
void nicif_n2d_done(volatile union cosim_eth_proto_n2d *msg);
void nicif_n2d_next(void);

volatile union cosim_eth_proto_d2n *nicsim_d2n_alloc(
        struct nicsim_params *params, uint64_t timestamp);

#endif /* ndef COSIM_NICSIM_H_ */
