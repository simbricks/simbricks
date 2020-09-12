#include <stdlib.h>
#include <string.h>
#include <cassert>
#include <iostream>

#include "i40e_bm.h"

#include "i40e_base_wrapper.h"

using namespace i40e;

extern nicbm::Runner *runner;

lan::lan(i40e_bm &dev_, size_t num_qs_)
    : dev(dev_), num_qs(num_qs_)
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
    for (size_t i = 0; i < num_qs; i++) {
        rxqs[i]->reset();
        txqs[i]->reset();
    }
}

void lan::qena_updated(uint16_t idx, bool rx)
{
#ifdef DEBUG_LAN
    std::cerr << "lan: qena updated idx=" << idx << " rx=" << rx << std::endl;
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
    std::cerr << "lan: tail updated idx=" << idx << " rx=" << rx << std::endl;
#endif

    lan_queue_base &q = (rx ? static_cast<lan_queue_base &>(*rxqs[idx]) :
        static_cast<lan_queue_base &>(*txqs[idx]));

    if (q.is_enabled())
        q.reg_updated();
}

void lan::packet_received(const void *data, size_t len)
{
#ifdef DEBUG_LAN
    std::cerr << "lan: packet received len=" << len << std::endl;
#endif

    // TODO: steering
    rxqs[0]->packet_received(data, len);
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
    std::cerr << qname << ": lan enabling queue " << idx << std::endl;
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
    std::cerr << qname << ": lan ctx fetched " << idx << std::endl;
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
    std::cerr << qname << ": lan disabling queue " << idx << std::endl;
#endif
    enabled = false;
    // TODO: write back
    reg_ena &= ~I40E_QRX_ENA_QENA_STAT_MASK;
}

void lan_queue_base::interrupt()
{
    uint32_t qctl = reg_intqctl;
#ifdef DEBUG_LAN
    std::cerr << qname << ": interrupt intctl=" << qctl << std::endl;
#endif

    uint16_t msix_idx = (qctl & I40E_QINT_TQCTL_MSIX_INDX_MASK) >>
        I40E_QINT_TQCTL_ITR_INDX_SHIFT;
    uint8_t msix0_idx = (qctl & I40E_QINT_TQCTL_MSIX0_INDX_MASK) >>
        I40E_QINT_TQCTL_MSIX0_INDX_SHIFT;
    bool cause_ena = !!(qctl & I40E_QINT_TQCTL_CAUSE_ENA_MASK);

    if (!cause_ena) {
#ifdef DEBUG_LAN
        std::cerr << qname << ": interrupt cause disabled" << std::endl;
#endif
        return;
    }

    if (msix_idx != 0) {
        std::cerr << "TODO: only int 0 is supported" << std::endl;
        abort();
    }

    // TODO throttling?
#ifdef DEBUG_LAN
    std::cerr << qname << ":   setting int0.qidx=" << msix0_idx << std::endl;
#endif
    lanmgr.dev.regs.pfint_icr0 |= I40E_PFINT_ICR0_INTEVENT_MASK |
        (1 << (I40E_PFINT_ICR0_QUEUE_0_SHIFT + msix0_idx));
    runner->msi_issue(0);
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
    std::cerr << qname << ": initialize()" << std::endl;
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
        std::cerr << "lan_queue_rx::initialize: currently only 32B descs "
            " supported" << std::endl;
        abort();
    }
    if (dtype != 0) {
        std::cerr << "lan_queue_rx::initialize: no header split supported"
            << std::endl;
        abort();
    }

#ifdef DEBUG_LAN
    std::cerr << qname << ":  head=" << reg_dummy_head << " base=" << base <<
        " len=" << len << " dbsz=" << dbuff_size << " hbsz=" << hbuff_size <<
        " dtype=" << (unsigned) dtype << " longdesc=" << longdesc <<
        " crcstrip=" << crc_strip << " rxmax=" << rxmax << std::endl;
#endif
}

queue_base::desc_ctx &lan_queue_rx::desc_ctx_create()
{
    return *new rx_desc_ctx(*this);
}

void lan_queue_rx::packet_received(const void *data, size_t pktlen)
{
    if (dcache.empty()) {
#ifdef DEBUG_LAN
        std::cerr << qname << ": empty, dropping packet" << std::endl;
#endif
        return;
    }

    rx_desc_ctx &ctx = *dcache.front();

#ifdef DEBUG_LAN
    std::cerr << qname << ": packet received didx=" << ctx.index << " cnt=" <<
        dcache.size() << std::endl;
#endif

    dcache.pop_front();
    ctx.packet_received(data, pktlen);
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

void lan_queue_rx::rx_desc_ctx::packet_received(const void *data, size_t pktlen)
{
    union i40e_32byte_rx_desc *rxd = reinterpret_cast<
        union i40e_32byte_rx_desc *> (desc);

    uint64_t addr = rxd->read.pkt_addr;

    memset(rxd, 0, sizeof(*rxd));
    rxd->wb.qword1.status_error_len |= (1 << I40E_RX_DESC_STATUS_DD_SHIFT);
    rxd->wb.qword1.status_error_len |= (1 << I40E_RX_DESC_STATUS_EOF_SHIFT);
    // TODO: only if checksums are correct
    rxd->wb.qword1.status_error_len |= (1 << I40E_RX_DESC_STATUS_L3L4P_SHIFT);
    rxd->wb.qword1.status_error_len |= (pktlen << I40E_RXD_QW1_LENGTH_PBUF_SHIFT);

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
    ready_segments.clear();
    queue_base::reset();
}

void lan_queue_tx::initialize()
{
#ifdef DEBUG_LAN
    std::cerr << qname << ": initialize()" << std::endl;
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
    std::cerr << qname << ":  head=" << reg_dummy_head << " base=" << base <<
        " len=" << len << " hwb=" << hwb << " hwb_addr=" << hwb_addr <<
        std::endl;
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
        std::cerr << qname << ": hwb=" << *((uint32_t *) dma->data) << std::endl;
#endif
        runner->issue_dma(*dma);
    }
}

bool lan_queue_tx::trigger_tx_packet()
{
    size_t n = ready_segments.size();
    if (n == 0)
        return false;

    size_t dcnt;
    bool eop = false;
    uint64_t d1;
    uint16_t iipt, l4t, total_len = 0;
    for (dcnt = 0; dcnt < n && !eop; dcnt++) {
        tx_desc_ctx *rd = ready_segments.at(dcnt);

        d1 = rd->d->cmd_type_offset_bsz;
#ifdef DEBUG_LAN
        std::cerr << qname << ": data fetched didx=" << rd->index << " d1=" <<
            d1 << std::endl;
#endif

        uint16_t pkt_len = (d1 & I40E_TXD_QW1_TX_BUF_SZ_MASK) >>
            I40E_TXD_QW1_TX_BUF_SZ_SHIFT;
        if (total_len + pkt_len > MTU) {
            std::cerr << "txq: trigger_tx_packet too large" << std::endl;
            abort();
        }

        memcpy(pktbuf + total_len, rd->data, pkt_len);

        uint16_t cmd = (d1 & I40E_TXD_QW1_CMD_MASK) >> I40E_TXD_QW1_CMD_SHIFT;
        eop = (cmd & I40E_TX_DESC_CMD_EOP);
        iipt = cmd & (I40E_TX_DESC_CMD_IIPT_MASK);
        l4t = (cmd & I40E_TX_DESC_CMD_L4T_EOFT_MASK);

#ifdef DEBUG_LAN
        std::cerr << qname << ":    eop=" << eop << " len=" << pkt_len <<
            std::endl;
#endif

        total_len += pkt_len;
    }

    if (!eop)
        return false;

    uint32_t off = (d1 & I40E_TXD_QW1_OFFSET_MASK) >> I40E_TXD_QW1_OFFSET_SHIFT;
    uint16_t maclen = ((off & I40E_TXD_QW1_MACLEN_MASK) >>
        I40E_TX_DESC_LENGTH_MACLEN_SHIFT) * 2;
    uint16_t iplen = ((off & I40E_TXD_QW1_IPLEN_MASK) >>
        I40E_TX_DESC_LENGTH_IPLEN_SHIFT) * 4;
    /*uint16_t l4len = (off & I40E_TXD_QW1_L4LEN_MASK) >>
        I40E_TX_DESC_LENGTH_L4_FC_LEN_SHIFT;*/


    if (l4t == I40E_TX_DESC_CMD_L4T_EOFT_TCP) {
        uint16_t tcp_off = maclen + iplen;
        xsum_tcp(pktbuf + tcp_off, total_len - tcp_off);
    }
#ifdef DEBUG_LAN
    std::cerr << qname << ":    iipt=" << iipt << " l4t=" << l4t <<
        " maclen=" << maclen << " iplen=" << iplen<< std::endl;
#else
    (void) iipt;
#endif

    runner->eth_send(pktbuf, total_len);

    while (dcnt-- > 0) {
        ready_segments.front()->processed();
        ready_segments.pop_front();
    }

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
    std::cerr << queue.qname << ": desc fetched didx=" << index << " d1=" <<
        d1 << std::endl;
#endif

    uint8_t dtype = (d1 & I40E_TXD_QW1_DTYPE_MASK) >> I40E_TXD_QW1_DTYPE_SHIFT;
    if (dtype == I40E_TX_DESC_DTYPE_DATA) {
        uint16_t len = (d1 & I40E_TXD_QW1_TX_BUF_SZ_MASK) >>
            I40E_TXD_QW1_TX_BUF_SZ_SHIFT;

#ifdef DEBUG_LAN
        std::cerr << queue.qname << ":  bufaddr=" << d->buffer_addr <<
            " len=" << len << std::endl;
#endif

        data_fetch(d->buffer_addr, len);
    } else if (dtype == I40E_TX_DESC_DTYPE_CONTEXT) {
        struct i40e_tx_context_desc *ctxd =
            reinterpret_cast<struct i40e_tx_context_desc *> (d);
        std::cerr << "  context descriptor: tp=" << ctxd->tunneling_params <<
            " l2t=" << ctxd->l2tag2 << " tctm=" << ctxd->type_cmd_tso_mss << std::endl;
        abort();

        /*desc->buffer_addr = 0;
        desc->cmd_type_offset_bsz = I40E_TX_DESC_DTYPE_DESC_DONE <<
            I40E_TXD_QW1_DTYPE_SHIFT;

        desc_writeback(desc_buf, didx);*/
    } else {
        std::cerr << "txq: only support context & data descriptors" << std::endl;
        abort();
    }

}

void lan_queue_tx::tx_desc_ctx::process()
{
    tq.ready_segments.push_back(this);
    tq.trigger_tx();
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
    std::cerr << queue.qname << ": tx head written back" << std::endl;
#endif
    queue.writeback_done(pos, cnt);
    delete this;
}
