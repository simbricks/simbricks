/* SPDX-License-Identifier: BSD-3-Clause
 * Copyright(c) 1982, 1986, 1990, 1993
 *      The Regents of the University of California.
 * Copyright(c) 2010-2014 Intel Corporation.
 * Copyright(c) 2014 6WIND S.A.
 * All rights reserved.
 */

#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <cassert>
#include <iostream>

#include "sims/nic/i40e_bm/i40e_bm.h"

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
struct ipv4_hdr {
        uint8_t  version_ihl;           /**< version and header length */
        uint8_t  type_of_service;       /**< type of service */
        uint16_t total_length;          /**< length of packet */
        uint16_t packet_id;             /**< packet ID */
        uint16_t fragment_offset;       /**< fragmentation offset */
        uint8_t  time_to_live;          /**< time to live */
        uint8_t  next_proto_id;         /**< protocol ID */
        uint16_t hdr_checksum;          /**< header checksum */
        uint32_t src_addr;              /**< source address */
        uint32_t dst_addr;              /**< destination address */
} __attribute__((packed));

static inline uint32_t __rte_raw_cksum(const void *buf, size_t len,
        uint32_t sum)
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

static inline uint16_t rte_ipv4_phdr_cksum(const struct ipv4_hdr *ipv4_hdr)
{
        struct ipv4_psd_header {
                uint32_t src_addr; /* IP address of source host. */
                uint32_t dst_addr; /* IP address of destination host. */
                uint8_t  zero;     /* zero. */
                uint8_t  proto;    /* L4 protocol type. */
                uint16_t len;      /* L4 length. */
        } psd_hdr;

        psd_hdr.src_addr = ipv4_hdr->src_addr;
        psd_hdr.dst_addr = ipv4_hdr->dst_addr;
        psd_hdr.zero = 0;
        psd_hdr.proto = ipv4_hdr->next_proto_id;
        psd_hdr.len = htons(
                (uint16_t)(ntohs(ipv4_hdr->total_length)
                        - sizeof(struct ipv4_hdr)));
        return rte_raw_cksum(&psd_hdr, sizeof(psd_hdr));
}


void xsum_tcp(void *tcphdr, size_t l4_len)
{
    struct rte_tcp_hdr *tcph = reinterpret_cast<struct rte_tcp_hdr *> (tcphdr);
    uint32_t cksum = rte_raw_cksum(tcphdr, l4_len);
    cksum = ((cksum & 0xffff0000) >> 16) + (cksum & 0xffff);
    cksum = (~cksum) & 0xffff;
    tcph->cksum = cksum;
}

void xsum_tcpip_tso(void *iphdr, uint8_t iplen, uint8_t l4len,
        uint16_t paylen)
{
    struct ipv4_hdr *ih = (struct ipv4_hdr *) iphdr;
    struct rte_tcp_hdr *tcph = (struct rte_tcp_hdr *)
        ((uint8_t *) iphdr + iplen);
    uint32_t cksum;

    // calculate ip xsum
    ih->total_length = htons(iplen + l4len + paylen);
    ih->hdr_checksum = 0;
    cksum = rte_raw_cksum(iphdr, iplen);
    cksum = ((cksum & 0xffff0000) >> 16) + (cksum & 0xffff);
    cksum = (~cksum) & 0xffff;
    ih->hdr_checksum = cksum;

    // calculate tcp xsum
    tcph->cksum = 0;
    cksum = rte_raw_cksum(tcph, l4len + paylen);
    cksum += rte_ipv4_phdr_cksum(ih);
    cksum = ((cksum & 0xffff0000) >> 16) + (cksum & 0xffff);
    cksum = (~cksum) & 0xffff;
    tcph->cksum = cksum;
}

void tso_postupdate_header(void *iphdr, uint8_t iplen, uint8_t l4len,
        uint16_t paylen)
{
    struct ipv4_hdr *ih = (struct ipv4_hdr *) iphdr;
    struct rte_tcp_hdr *tcph = (struct rte_tcp_hdr *)
        ((uint8_t *) iphdr + iplen);
    tcph->sent_seq = htonl(ntohl(tcph->sent_seq) + paylen);
    ih->packet_id = htons(ntohs(ih->packet_id) + 1);
}

}  // namespace i40e
