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

#pragma once

#include <stdint.h>

namespace headers {

/******************************************************************************/
/* Ethernet */

#define ETH_ADDR_LEN 6

#define ETH_TYPE_IP   0x0800
#define ETH_TYPE_ARP  0x0806

struct eth_addr {
  uint8_t addr[ETH_ADDR_LEN];
} __attribute__ ((packed));

struct eth_hdr {
  struct eth_addr dest;
  struct eth_addr src;
  uint16_t type;
} __attribute__ ((packed));


/******************************************************************************/
/* IPv4 */

#define IPH_V(hdr)  ((hdr)->_v_hl >> 4)
#define IPH_HL(hdr) ((hdr)->_v_hl & 0x0f)
#define IPH_TOS(hdr) ((hdr)->_tos)
#define IPH_ECN(hdr) ((hdr)->_tos & 0x3)

#define IPH_VHL_SET(hdr, v, hl) (hdr)->_v_hl = (((v) << 4) | (hl))
#define IPH_TOS_SET(hdr, tos) (hdr)->_tos = (tos)
#define IPH_ECN_SET(hdr, e) (hdr)->_tos = ((hdr)->_tos & 0xffc) | (e)

#define IP_HLEN 20

#define IP_PROTO_IP      0
#define IP_PROTO_ICMP    1
#define IP_PROTO_IGMP    2
#define IP_PROTO_IPENCAP 4
#define IP_PROTO_UDP     17
#define IP_PROTO_UDPLITE 136
#define IP_PROTO_TCP     6
#define IP_PROTO_DCCP	 33

#define IP_ECN_NONE      0x0
#define IP_ECN_ECT0      0x2
#define IP_ECN_ECT1      0x1
#define IP_ECN_CE        0x3

struct ip_hdr {
  /* version / header length */
  uint8_t _v_hl;
  /* type of service */
  uint8_t _tos;
  /* total length */
  uint16_t len;
  /* identification */
  uint16_t id;
  /* fragment offset field */
  uint16_t offset;
  /* time to live */
  uint8_t ttl;
  /* protocol*/
  uint8_t proto;
  /* checksum */
  uint16_t chksum;
  /* source and destination IP addresses */
  uint32_t src;
  uint32_t dest;
} __attribute__ ((packed));


/******************************************************************************/
/* ARP */

#define ARP_OPER_REQUEST 1
#define ARP_OPER_REPLY 2
#define ARP_HTYPE_ETHERNET 1
#define ARP_PTYPE_IPV4 0x0800

struct arp_hdr {
  uint16_t htype;
  uint16_t ptype;
  uint8_t hlen;
  uint8_t plen;
  uint16_t oper;
  struct eth_addr sha;
  uint32_t spa;
  struct eth_addr tha;
  uint32_t tpa;
} __attribute__((packed));


/******************************************************************************/
/* TCP */

#define TCP_FIN 0x01U
#define TCP_SYN 0x02U
#define TCP_RST 0x04U
#define TCP_PSH 0x08U
#define TCP_ACK 0x10U
#define TCP_URG 0x20U
#define TCP_ECE 0x40U
#define TCP_CWR 0x80U
#define TCP_NS  0x100U

#define TCP_FLAGS 0x1ffU

/* Length of the TCP header, excluding options. */
#define TCP_HLEN 20

#define TCPH_HDRLEN(phdr) (ntohs((phdr)->_hdrlen_rsvd_flags) >> 12)
#define TCPH_FLAGS(phdr)  (ntohs((phdr)->_hdrlen_rsvd_flags) & TCP_FLAGS)

#define TCPH_HDRLEN_SET(phdr, len) (phdr)->_hdrlen_rsvd_flags = htons(((len) << 12) | TCPH_FLAGS(phdr))
#define TCPH_FLAGS_SET(phdr, flags) (phdr)->_hdrlen_rsvd_flags = (((phdr)->_hdrlen_rsvd_flags & PP_HTONS((uint16_t)(~(uint16_t)(TCP_FLAGS)))) | htons(flags))
#define TCPH_HDRLEN_FLAGS_SET(phdr, len, flags) (phdr)->_hdrlen_rsvd_flags = htons(((len) << 12) | (flags))

#define TCPH_SET_FLAG(phdr, flags ) (phdr)->_hdrlen_rsvd_flags = ((phdr)->_hdrlen_rsvd_flags | htons(flags))
#define TCPH_UNSET_FLAG(phdr, flags) (phdr)->_hdrlen_rsvd_flags = htons(ntohs((phdr)->_hdrlen_rsvd_flags) | (TCPH_FLAGS(phdr) & ~(flags)) )

#define TCP_TCPLEN(seg) ((seg)->len + ((TCPH_FLAGS((seg)->tcphdr) & (TCP_FIN | TCP_SYN)) != 0))

struct tcp_hdr {
  uint16_t src;
  uint16_t dest;
  uint32_t seqno;
  uint32_t ackno;
  uint16_t _hdrlen_rsvd_flags;
  uint16_t wnd;
  uint16_t chksum;
  uint16_t urgp;
} __attribute__((packed));


/******************************************************************************/
/* UDP */

struct udp_hdr {
  uint16_t src;
  uint16_t dest;
  uint16_t len;
  uint16_t chksum;
} __attribute__((packed));


/******************************************************************************/
/* whole packets */

struct pkt_arp {
  struct eth_hdr eth;
  struct arp_hdr arp;
} __attribute__ ((packed));

struct pkt_ip {
  struct eth_hdr eth;
  struct ip_hdr  ip;
} __attribute__ ((packed));

struct pkt_tcp {
  struct eth_hdr eth;
  struct ip_hdr  ip;
  struct tcp_hdr tcp;
} __attribute__ ((packed));

struct pkt_udp {
  struct eth_hdr eth;
  struct ip_hdr  ip;
  struct udp_hdr udp;
} __attribute__ ((packed));

} // namespace headers
