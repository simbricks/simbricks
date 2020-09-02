/* SPDX-License-Identifier: BSD-3-Clause
 * Copyright(c) 1982, 1986, 1990, 1993
 *      The Regents of the University of California.
 * Copyright(c) 2010-2014 Intel Corporation.
 * Copyright(c) 2014 6WIND S.A.
 * All rights reserved.
 */

#include <stdlib.h>
#include <string.h>
#include <cassert>
#include <iostream>

#include "i40e_bm.h"

namespace i40e {

/* from dpdk/lib/librte_net/rte_tcp.h */
struct rte_tcp_hdr {
    uint16_t src_port; /**< TCP source port. */
    uint16_t dst_port; /**< TCP destination port. */
    uint32_t sent_seq; /**< TX data sequence number. */
    uint32_t recv_ack; /**< RX data acknowledgment sequence number. */
    uint8_t  data_off;   /**< Data offset. */
    uint8_t  tcp_flags;  /**< TCP flags */
    uint16_t rx_win;   /**< RX flow control window. */
    uint16_t cksum;    /**< TCP checksum. */
    uint16_t tcp_urp;  /**< TCP urgent pointer, if any. */
} __attribute__((packed));


/* from dpdk/lib/librte_net/rte_ip.h */
static inline uint32_t __rte_raw_cksum(const void *buf, size_t len, uint32_t sum)
{
    /* workaround gcc strict-aliasing warning */
    uintptr_t ptr = (uintptr_t)buf;
    typedef uint16_t __attribute__((__may_alias__)) u16_p;
    const u16_p *u16_buf = (const u16_p *)ptr;

    while (len >= (sizeof(*u16_buf) * 4)) {
        sum += u16_buf[0];
        sum += u16_buf[1];
        sum += u16_buf[2];
        sum += u16_buf[3];
        len -= sizeof(*u16_buf) * 4;
        u16_buf += 4;
    }
    while (len >= sizeof(*u16_buf)) {
        sum += *u16_buf;
        len -= sizeof(*u16_buf);
        u16_buf += 1;
    }

    /* if length is in odd bytes */
    if (len == 1) {
        uint16_t left = 0;
        *(uint8_t *)&left = *(const uint8_t *)u16_buf;
        sum += left;
    }

    return sum;
}

static inline uint16_t __rte_raw_cksum_reduce(uint32_t sum)
{
    sum = ((sum & 0xffff0000) >> 16) + (sum & 0xffff);
    sum = ((sum & 0xffff0000) >> 16) + (sum & 0xffff);
    return (uint16_t)sum;
}

static inline uint16_t rte_raw_cksum(const void *buf, size_t len)
{
    uint32_t sum;

    sum = __rte_raw_cksum(buf, len, 0);
    return __rte_raw_cksum_reduce(sum);
}

void xsum_tcp(void *tcphdr, size_t l4_len)
{
    struct rte_tcp_hdr *tcph = reinterpret_cast<struct rte_tcp_hdr *> (tcphdr);
    uint32_t cksum = rte_raw_cksum(tcphdr, l4_len);
	cksum = ((cksum & 0xffff0000) >> 16) + (cksum & 0xffff);
	cksum = (~cksum) & 0xffff;
    tcph->cksum = cksum;
}

}
