#include <stdlib.h>
#include <string.h>
#include <cassert>
#include <iostream>
#include <arpa/inet.h>

#include "i40e_bm.h"

#include "i40e_base_wrapper.h"
#include "headers.h"

using namespace i40e;

extern nicbm::Runner *runner;

lan::lan(i40e_bm &dev_, size_t num_qs_)
    : dev(dev_), log("lan"), rss_kc(dev_.regs.glqf_hkey), num_qs(num_qs_)
{
    rxqs = new lan_queue_rx *[num_qs];
    txqs = new lan_queue_tx *[num_qs];

    for (size_t i = 0; i < num_qs; i++) {
        rxqs[i] = new lan_queue_rx(*this, dev.regs.qrx_tail[i], i,
                dev.regs.qrx_ena[i], dev.regs.glhmc_lanrxbase[0],
                dev.regs.qint_rqctl[i]);
        txqs[i] = new lan_queue_tx(*this, dev.regs.qtx_tail[i], i,
                dev.regs.qtx_ena[i], dev.regs.glhmc_lantxbase[0],
                dev.regs.qint_tqctl[i]);
    }
}

void lan::reset()
{
    rss_kc.set_dirty();
    for (size_t i = 0; i < num_qs; i++) {
        rxqs[i]->reset();
        txqs[i]->reset();
    }
}

void lan::qena_updated(uint16_t idx, bool rx)
{
#ifdef DEBUG_LAN
    log << " qena updated idx=" << idx << " rx=" << rx << logger::endl;
#endif
    uint32_t &reg = (rx ? dev.regs.qrx_ena[idx] : dev.regs.qtx_ena[idx]);
    lan_queue_base &q = (rx ? static_cast<lan_queue_base &>(*rxqs[idx]) :
        static_cast<lan_queue_base &>(*txqs[idx]));

    if ((reg & I40E_QRX_ENA_QENA_REQ_MASK) && !q.is_enabled()) {
        q.enable();
    } else if (!(reg & I40E_QRX_ENA_QENA_REQ_MASK) && q.is_enabled()) {
        q.disable();
    }
}

void lan::tail_updated(uint16_t idx, bool rx)
{
#ifdef DEBUG_LAN
    log << " tail updated idx=" << idx << " rx=" << rx << logger::endl;
#endif

    lan_queue_base &q = (rx ? static_cast<lan_queue_base &>(*rxqs[idx]) :
        static_cast<lan_queue_base &>(*txqs[idx]));

    if (q.is_enabled())
        q.reg_updated();
}

void lan::rss_key_updated()
{
    rss_kc.set_dirty();
}

bool lan::rss_steering(const void *data, size_t len, uint16_t &queue,
        uint32_t &hash)
{
    hash = 0;

    const headers::pkt_tcp *tcp = reinterpret_cast<const headers::pkt_tcp *> (data);
    const headers::pkt_udp *udp = reinterpret_cast<const headers::pkt_udp *> (data);

    // should actually determine packet type and mask with enabled packet types
    // TODO: ipv6
    if (tcp->eth.type == htons(ETH_TYPE_IP) &&
            tcp->ip.proto == IP_PROTO_TCP)
    {
        hash = rss_kc.hash_ipv4(ntohl(tcp->ip.src), ntohl(tcp->ip.dest),
                ntohs(tcp->tcp.src), ntohs(tcp->tcp.dest));
    } else if (udp->eth.type == htons(ETH_TYPE_IP) &&
            udp->ip.proto == IP_PROTO_UDP)
    {
        hash = rss_kc.hash_ipv4(ntohl(udp->ip.src), ntohl(udp->ip.dest),
                ntohs(udp->udp.src), ntohs(udp->udp.dest));
    } else if (udp->eth.type == htons(ETH_TYPE_IP)) {
        hash = rss_kc.hash_ipv4(ntohl(udp->ip.src), ntohl(udp->ip.dest), 0, 0);
    } else {
        return false;
    }

    uint16_t luts = (!(dev.regs.pfqf_ctl_0 & I40E_PFQF_CTL_0_HASHLUTSIZE_MASK) ?
            128 : 512);
    uint16_t idx = hash % luts;
    queue = (dev.regs.pfqf_hlut[idx / 4] >> (8 * (idx % 4))) & 0x3f;
    return true;
}

void lan::packet_received(const void *data, size_t len)
{
#ifdef DEBUG_LAN
    log << " packet received len=" << len << logger::endl;
#endif

    uint32_t hash = 0;
    uint16_t queue = 0;
    rss_steering(data, len, queue, hash);
    rxqs[queue]->packet_received(data, len, hash);
}

lan_queue_base::lan_queue_base(lan &lanmgr_, const std::string &qtype,
        uint32_t &reg_tail_, size_t idx_,
        uint32_t &reg_ena_, uint32_t &fpm_basereg_, uint32_t &reg_intqctl_,
        uint16_t ctx_size_)
    : queue_base(qtype + std::to_string(idx_), reg_dummy_head, reg_tail_),
    lanmgr(lanmgr_), enabling(false),
    idx(idx_), reg_ena(reg_ena_), fpm_basereg(fpm_basereg_),
    reg_intqctl(reg_intqctl_), ctx_size(ctx_size_)
{
    ctx = new uint8_t[ctx_size_];
}

void lan_queue_base::reset()
{
    enabling = false;
    queue_base::reset();
}

void lan_queue_base::enable()
{
    if (enabling || enabled)
        return;

#ifdef DEBUG_LAN
    log << " lan enabling queue " << idx << logger::endl;
#endif
    enabling = true;

    qctx_fetch *qf = new qctx_fetch(*this);
    qf->write = false;
    qf->dma_addr = ((fpm_basereg & I40E_GLHMC_LANTXBASE_FPMLANTXBASE_MASK) >>
        I40E_GLHMC_LANTXBASE_FPMLANTXBASE_SHIFT) * 512;
    qf->dma_addr += ctx_size * idx;
    qf->len = ctx_size;
    qf->data = ctx;

    lanmgr.dev.hmc.issue_mem_op(*qf);
}

void lan_queue_base::ctx_fetched()
{
#ifdef DEBUG_LAN
    log << " lan ctx fetched " << idx << logger::endl;
#endif

    initialize();

    enabling = false;
    enabled = true;
    reg_ena |= I40E_QRX_ENA_QENA_STAT_MASK;

    reg_updated();
}

void lan_queue_base::disable()
{
#ifdef DEBUG_LAN
    log << " lan disabling queue " << idx << logger::endl;
#endif
    enabled = false;
    // TODO: write back
    reg_ena &= ~I40E_QRX_ENA_QENA_STAT_MASK;
}

void lan_queue_base::interrupt()
{
    uint32_t qctl = reg_intqctl;
    uint32_t gctl = lanmgr.dev.regs.pfint_dyn_ctl0;
#ifdef DEBUG_LAN
    log << " interrupt qctl=" << qctl << " gctl=" << gctl << logger::endl;
#endif

    uint16_t msix_idx = (qctl & I40E_QINT_TQCTL_MSIX_INDX_MASK) >>
        I40E_QINT_TQCTL_ITR_INDX_SHIFT;
    uint8_t msix0_idx = (qctl & I40E_QINT_TQCTL_MSIX0_INDX_MASK) >>
        I40E_QINT_TQCTL_MSIX0_INDX_SHIFT;

    if (msix_idx != 0) {
        log << "TODO: only int 0 is supported" << logger::endl;
        abort();
    }

    bool cause_ena = !!(qctl & I40E_QINT_TQCTL_CAUSE_ENA_MASK) &&
      !!(gctl & I40E_PFINT_DYN_CTL0_INTENA_MASK);
    if (!cause_ena) {
#ifdef DEBUG_LAN
        log << " interrupt cause disabled" << logger::endl;
#endif
        return;
    }

    // TODO throttling?
#ifdef DEBUG_LAN
    log << "   setting int0.qidx=" << msix0_idx << logger::endl;
#endif
    lanmgr.dev.regs.pfint_icr0 |= I40E_PFINT_ICR0_INTEVENT_MASK |
        (1 << (I40E_PFINT_ICR0_QUEUE_0_SHIFT + msix0_idx));

    uint8_t itr = (qctl & I40E_QINT_TQCTL_ITR_INDX_MASK) >>
        I40E_QINT_TQCTL_ITR_INDX_SHIFT;
    lanmgr.dev.signal_interrupt(0, itr);

}

lan_queue_base::qctx_fetch::qctx_fetch(lan_queue_base &lq_)
    : lq(lq_)
{
}

void lan_queue_base::qctx_fetch::done()
{
    lq.ctx_fetched();
    delete this;
}

lan_queue_rx::lan_queue_rx(lan &lanmgr_, uint32_t &reg_tail_, size_t idx_,
        uint32_t &reg_ena_, uint32_t &reg_fpmbase_, uint32_t &reg_intqctl_)
    : lan_queue_base(lanmgr_, "rxq", reg_tail_, idx_, reg_ena_, reg_fpmbase_,
            reg_intqctl_, 32)
{
    // use larger value for initialization
    desc_len = 32;
    ctxs_init();
}

void lan_queue_rx::reset()
{
    dcache.clear();
    queue_base::reset();
}

void lan_queue_rx::initialize()
{
#ifdef DEBUG_LAN
    log << " initialize()" << logger::endl;
#endif
    uint8_t *ctx_p = reinterpret_cast<uint8_t *>(ctx);

    uint16_t *head_p = reinterpret_cast<uint16_t *>(ctx_p + 0);
    uint64_t *base_p = reinterpret_cast<uint64_t *>(ctx_p + 4);
    uint16_t *qlen_p = reinterpret_cast<uint16_t *>(ctx_p + 11);
    uint16_t *dbsz_p = reinterpret_cast<uint16_t *>(ctx_p + 12);
    uint16_t *hbsz_p = reinterpret_cast<uint16_t *>(ctx_p + 13);
    uint32_t *rxmax_p = reinterpret_cast<uint32_t *>(ctx_p + 21);

    reg_dummy_head = (*head_p) & ((1 << 13) - 1);

    base = ((*base_p) & ((1ULL << 57) - 1)) * 128;
    len = (*qlen_p >> 1) & ((1 << 13) - 1);

    dbuff_size = (((*dbsz_p) >> 6) & ((1 << 7) - 1)) * 128;
    hbuff_size = (((*hbsz_p) >> 5) & ((1 << 5) - 1)) * 64;
    uint8_t dtype = ((*hbsz_p) >> 10) & ((1 << 2) - 1);
    bool longdesc = !!(((*hbsz_p) >> 12) & 0x1);
    desc_len = (longdesc ? 32 : 16);
    crc_strip = !!(((*hbsz_p) >> 13) & 0x1);
    rxmax = (((*rxmax_p) >> 6) & ((1 << 14) - 1)) * 128;

    if (!longdesc) {
        log << "lan_queue_rx::initialize: currently only 32B descs "
            " supported" << logger::endl;
        abort();
    }
    if (dtype != 0) {
        log << "lan_queue_rx::initialize: no header split supported"
            << logger::endl;
        abort();
    }

#ifdef DEBUG_LAN
    log << "  head=" << reg_dummy_head << " base=" << base <<
        " len=" << len << " dbsz=" << dbuff_size << " hbsz=" << hbuff_size <<
        " dtype=" << (unsigned) dtype << " longdesc=" << longdesc <<
        " crcstrip=" << crc_strip << " rxmax=" << rxmax << logger::endl;
#endif
}

queue_base::desc_ctx &lan_queue_rx::desc_ctx_create()
{
    return *new rx_desc_ctx(*this);
}

void lan_queue_rx::packet_received(const void *data, size_t pktlen, uint32_t h)
{
    size_t num_descs = (pktlen + dbuff_size - 1) / dbuff_size;

    if (!enabled)
        return;

    if (dcache.size() < num_descs) {
#ifdef DEBUG_LAN
        log << " not enough rx descs (" << num_descs << ", dropping packet" <<
            logger::endl;
#endif
        return;
    }

    for (size_t i = 0; i < num_descs; i++) {
        rx_desc_ctx &ctx = *dcache.front();

#ifdef DEBUG_LAN
        log << " packet part=" << i <<  " received didx=" << ctx.index <<
            " cnt=" << dcache.size() << logger::endl;
#endif
        dcache.pop_front();

        const uint8_t *buf = (const uint8_t *) data + (dbuff_size * i);
        if (i == num_descs - 1) {
            // last packet
            ctx.packet_received(buf, pktlen - dbuff_size * i, true);
        } else {
            ctx.packet_received(buf, dbuff_size, false);
        }
    }
}

lan_queue_rx::rx_desc_ctx::rx_desc_ctx(lan_queue_rx &queue_)
    : desc_ctx(queue_), rq(queue_)
{
}

void lan_queue_rx::rx_desc_ctx::data_written(uint64_t addr, size_t len)
{
    processed();
}

void lan_queue_rx::rx_desc_ctx::process()
{
    rq.dcache.push_back(this);
}

void lan_queue_rx::rx_desc_ctx::packet_received(const void *data,
        size_t pktlen, bool last)
{
    union i40e_32byte_rx_desc *rxd = reinterpret_cast<
        union i40e_32byte_rx_desc *> (desc);

    uint64_t addr = rxd->read.pkt_addr;

    memset(rxd, 0, sizeof(*rxd));
    rxd->wb.qword1.status_error_len |= (1 << I40E_RX_DESC_STATUS_DD_SHIFT);
    rxd->wb.qword1.status_error_len |= (pktlen << I40E_RXD_QW1_LENGTH_PBUF_SHIFT);

    if (last) {
        rxd->wb.qword1.status_error_len |= (1 << I40E_RX_DESC_STATUS_EOF_SHIFT);
        // TODO: only if checksums are correct
        rxd->wb.qword1.status_error_len |= (1 << I40E_RX_DESC_STATUS_L3L4P_SHIFT);
    }
    data_write(addr, pktlen, data);
}

lan_queue_tx::lan_queue_tx(lan &lanmgr_, uint32_t &reg_tail_, size_t idx_,
        uint32_t &reg_ena_, uint32_t &reg_fpmbase_, uint32_t &reg_intqctl)
    : lan_queue_base(lanmgr_, "txq", reg_tail_, idx_, reg_ena_, reg_fpmbase_,
            reg_intqctl, 128)
{
    desc_len = 16;
    ctxs_init();
}

void lan_queue_tx::reset()
{
    tso_off = 0;
    tso_len = 0;
    ready_segments.clear();
    queue_base::reset();
}

void lan_queue_tx::initialize()
{
#ifdef DEBUG_LAN
    log << " initialize()" << logger::endl;
#endif
    uint8_t *ctx_p = reinterpret_cast<uint8_t *>(ctx);

    uint16_t *head_p = reinterpret_cast<uint16_t *>(ctx_p + 0);
    uint64_t *base_p = reinterpret_cast<uint64_t *>(ctx_p + 4);
    uint16_t *hwb_qlen_p = reinterpret_cast<uint16_t *>(ctx_p + 20);
    uint64_t *hwb_addr_p = reinterpret_cast<uint64_t *>(ctx_p + 24);

    reg_dummy_head = (*head_p) & ((1 << 13) - 1);

    base = ((*base_p) & ((1ULL << 57) - 1)) * 128;
    len = ((*hwb_qlen_p) >> 1) & ((1 << 13) - 1);

    hwb = !!(*hwb_qlen_p & (1 << 0));
    hwb_addr = *hwb_addr_p;

#ifdef DEBUG_LAN
    log << "  head=" << reg_dummy_head << " base=" << base <<
        " len=" << len << " hwb=" << hwb << " hwb_addr=" << hwb_addr <<
        logger::endl;
#endif
}

queue_base::desc_ctx &lan_queue_tx::desc_ctx_create()
{
    return *new tx_desc_ctx(*this);
}

void lan_queue_tx::do_writeback(uint32_t first_idx, uint32_t first_pos,
        uint32_t cnt)
{
    if (!hwb) {
        // if head index writeback is disabled we need to write descriptor back
        lan_queue_base::do_writeback(first_idx, first_pos, cnt);
    } else {
        // else we just need to write the index back
        dma_hwb *dma = new dma_hwb(*this, first_pos, cnt,
                (first_idx + cnt) % len);
        dma->dma_addr = hwb_addr;

#ifdef DEBUG_LAN
        log << " hwb=" << *((uint32_t *) dma->data) << logger::endl;
#endif
        runner->issue_dma(*dma);
    }
}

bool lan_queue_tx::trigger_tx_packet()
{
    size_t n = ready_segments.size();
    size_t d_skip = 0, dcnt;
    bool eop = false;
    uint64_t d1;
    uint32_t iipt, l4t, pkt_len, total_len = 0, data_limit;
    bool tso = false;
    uint32_t tso_mss = 0, tso_paylen = 0;
    uint16_t maclen = 0, iplen = 0, l4len = 0;

    // abort if no queued up descriptors
    if (n == 0)
        return false;

#ifdef DEBUG_LAN
    log << "trigger_tx_packet(n=" << n << ", firstidx=" <<
        ready_segments.at(0)->index << ")" << logger::endl;
    log << "  tso_off=" << tso_off << " tso_len=" << tso_len << logger::endl;
#endif


    // check if we have a context descriptor first
    tx_desc_ctx *rd = ready_segments.at(0);
    uint8_t dtype = (rd->d->cmd_type_offset_bsz & I40E_TXD_QW1_DTYPE_MASK) >>
        I40E_TXD_QW1_DTYPE_SHIFT;
    if (dtype == I40E_TX_DESC_DTYPE_CONTEXT) {
        struct i40e_tx_context_desc *ctxd =
            reinterpret_cast<struct i40e_tx_context_desc *> (rd->d);
        d1 = ctxd->type_cmd_tso_mss;

        uint16_t cmd = ((d1 & I40E_TXD_CTX_QW1_CMD_MASK) >>
                I40E_TXD_CTX_QW1_CMD_SHIFT);
        tso = !!(cmd & I40E_TX_CTX_DESC_TSO);
        tso_mss = (d1 & I40E_TXD_CTX_QW1_MSS_MASK) >>
            I40E_TXD_CTX_QW1_MSS_SHIFT;

#ifdef DEBUG_LAN
        log << "  tso=" << tso << " mss=" << tso_mss << logger::endl;
#endif

        d_skip = 1;
    }

    // find EOP descriptor
    for (dcnt = d_skip; dcnt < n && !eop; dcnt++) {
        tx_desc_ctx *rd = ready_segments.at(dcnt);
        d1 = rd->d->cmd_type_offset_bsz;

#ifdef DEBUG_LAN
        log << " data fetched didx=" << rd->index << " d1=" <<
            d1 << logger::endl;
#endif

        dtype = (d1 & I40E_TXD_QW1_DTYPE_MASK) >> I40E_TXD_QW1_DTYPE_SHIFT;
        if (dtype != I40E_TX_DESC_DTYPE_DATA) {
            log << "trigger tx desc is not a data descriptor idx=" << rd->index
                << " d1=" << d1 << logger::endl;
            abort();
        }

        uint16_t cmd = (d1 & I40E_TXD_QW1_CMD_MASK) >> I40E_TXD_QW1_CMD_SHIFT;
        eop = (cmd & I40E_TX_DESC_CMD_EOP);
        iipt = cmd & (I40E_TX_DESC_CMD_IIPT_MASK);
        l4t = (cmd & I40E_TX_DESC_CMD_L4T_EOFT_MASK);

        if (eop) {
            uint32_t off = (d1 & I40E_TXD_QW1_OFFSET_MASK) >> I40E_TXD_QW1_OFFSET_SHIFT;
            maclen = ((off & I40E_TXD_QW1_MACLEN_MASK) >>
                I40E_TX_DESC_LENGTH_MACLEN_SHIFT) * 2;
            iplen = ((off & I40E_TXD_QW1_IPLEN_MASK) >>
                I40E_TX_DESC_LENGTH_IPLEN_SHIFT) * 4;
            l4len = ((off & I40E_TXD_QW1_L4LEN_MASK) >>
                I40E_TX_DESC_LENGTH_L4_FC_LEN_SHIFT) * 4;
        }

        pkt_len = (d1 & I40E_TXD_QW1_TX_BUF_SZ_MASK) >>
            I40E_TXD_QW1_TX_BUF_SZ_SHIFT;
        total_len += pkt_len;

#ifdef DEBUG_LAN
        log << "    eop=" << eop << " len=" << pkt_len << logger::endl;
#endif
    }

    // Unit not completely fetched yet
    if (!eop)
        return false;

    if (tso) {
        if (tso_off == 0)
            data_limit = maclen + iplen + l4len + tso_mss;
        else
            data_limit = tso_off + tso_mss;

        if (data_limit > total_len) {
            data_limit = total_len;
        }
    } else {
        if (total_len > MTU) {
            log << "    packet is longer (" << total_len << ") than MTU (" <<
                MTU << ")" << logger::endl;
            abort();
        }
        data_limit = total_len;
    }

#ifdef DEBUG_LAN
    log << "    iipt=" << iipt << " l4t=" << l4t <<
        " maclen=" << maclen << " iplen=" << iplen << " l4len=" << l4len <<
        " total_len=" << total_len << " data_limit=" << data_limit <<
        logger::endl;

#else
    (void) iipt;
#endif


    // copy data for this segment
    uint32_t off = 0;
    for (dcnt = d_skip; dcnt < n && off < data_limit; dcnt++) {
        tx_desc_ctx *rd = ready_segments.at(dcnt);
        d1 = rd->d->cmd_type_offset_bsz;
        uint16_t pkt_len = (d1 & I40E_TXD_QW1_TX_BUF_SZ_MASK) >>
            I40E_TXD_QW1_TX_BUF_SZ_SHIFT;

        if (off <= tso_off && off + pkt_len > tso_off) {
            uint32_t start = tso_off;
            uint32_t end = off + pkt_len;
            if (end > data_limit)
                end = data_limit;

#ifdef DEBUG_LAN
        log << "    copying data from off=" << off << " idx=" << rd->index <<
            " start=" << start << " end=" << end << " tso_len=" << tso_len <<
            logger::endl;
#endif

            memcpy(pktbuf + tso_len, (uint8_t *) rd->data + (start - off),
                    end - start);
            tso_off = end;
            tso_len += end - start;
        }

        off += pkt_len;
    }

    assert(tso_len <= MTU);

    if (!tso) {
#ifdef DEBUG_LAN
        log << "    normal non-tso packet" << logger::endl;
#endif

        if (l4t == I40E_TX_DESC_CMD_L4T_EOFT_TCP) {
            uint16_t tcp_off = maclen + iplen;
            xsum_tcp(pktbuf + tcp_off, tso_len - tcp_off);
        }

        runner->eth_send(pktbuf, tso_len);
    } else {
#ifdef DEBUG_LAN
        log << "    tso packet off=" << tso_off << " len=" << tso_len <<
            logger::endl;
#endif

        // TSO gets hairier
        uint16_t hdrlen = maclen + iplen + l4len;

        // calculate payload size
        tso_paylen = tso_len - hdrlen;
        if (tso_paylen > tso_mss)
            tso_paylen = tso_mss;

        xsum_tcpip_tso(pktbuf + maclen, iplen, l4len, tso_paylen);

        runner->eth_send(pktbuf, tso_len);

        tso_postupdate_header(pktbuf + maclen, iplen, l4len, tso_paylen);

        // not done yet with this TSO unit
        if (tso && tso_off < total_len) {
            tso_len = hdrlen;
            return true;
        }
    }

#ifdef DEBUG_LAN
        log << "    unit done" << logger::endl;
#endif
    while (dcnt-- > 0) {
        ready_segments.front()->processed();
        ready_segments.pop_front();
    }

    tso_len = 0;
    tso_off = 0;

    return true;
}

void lan_queue_tx::trigger_tx()
{
    while (trigger_tx_packet());
}

lan_queue_tx::tx_desc_ctx::tx_desc_ctx(lan_queue_tx &queue_)
    : desc_ctx(queue_), tq(queue_)
{
    d = reinterpret_cast<struct i40e_tx_desc *>(desc);
}

void lan_queue_tx::tx_desc_ctx::prepare()
{
    uint64_t d1 = d->cmd_type_offset_bsz;

#ifdef DEBUG_LAN
    queue.log << " desc fetched didx=" << index << " d1=" <<
        d1 << logger::endl;
#endif

    uint8_t dtype = (d1 & I40E_TXD_QW1_DTYPE_MASK) >> I40E_TXD_QW1_DTYPE_SHIFT;
    if (dtype == I40E_TX_DESC_DTYPE_DATA) {
        uint16_t len = (d1 & I40E_TXD_QW1_TX_BUF_SZ_MASK) >>
            I40E_TXD_QW1_TX_BUF_SZ_SHIFT;

#ifdef DEBUG_LAN
        queue.log << "  bufaddr=" << d->buffer_addr <<
            " len=" << len << logger::endl;
#endif

        data_fetch(d->buffer_addr, len);
    } else if (dtype == I40E_TX_DESC_DTYPE_CONTEXT) {
#ifdef DEBUG_LAN
        struct i40e_tx_context_desc *ctxd =
            reinterpret_cast<struct i40e_tx_context_desc *> (d);
        queue.log << "  context descriptor: tp=" << ctxd->tunneling_params <<
            " l2t=" << ctxd->l2tag2 << " tctm=" << ctxd->type_cmd_tso_mss << logger::endl;
#endif

        prepared();
    } else {
        queue.log << "txq: only support context & data descriptors" << logger::endl;
        abort();
    }

}

void lan_queue_tx::tx_desc_ctx::process()
{
    tq.ready_segments.push_back(this);
    tq.trigger_tx();
}

void lan_queue_tx::tx_desc_ctx::processed()
{
    d->cmd_type_offset_bsz = I40E_TX_DESC_DTYPE_DESC_DONE <<
        I40E_TXD_QW1_DTYPE_SHIFT;
    desc_ctx::processed();
}

lan_queue_tx::dma_hwb::dma_hwb(lan_queue_tx &queue_, uint32_t pos_,
        uint32_t cnt_, uint32_t nh_)
    : queue(queue_), pos(pos_), cnt(cnt_), next_head(nh_)
{
    data = &next_head;
    len = 4;
    write = true;
}

lan_queue_tx::dma_hwb::~dma_hwb()
{
}

void lan_queue_tx::dma_hwb::done()
{
#ifdef DEBUG_LAN
    queue.log << " tx head written back" << logger::endl;
#endif
    queue.writeback_done(pos, cnt);
    queue.trigger();
    delete this;
}
