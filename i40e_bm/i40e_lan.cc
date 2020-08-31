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
                dev.regs.qrx_ena[i], dev.regs.glhmc_lanrxbase[0]);
        txqs[i] = new lan_queue_tx(*this, dev.regs.qtx_tail[i], i,
                dev.regs.qtx_ena[i], dev.regs.glhmc_lantxbase[0]);
    }
}

void lan::qena_updated(uint16_t idx, bool rx)
{
    std::cerr << "lan: qena updated idx=" << idx << " rx=" << rx << std::endl;
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
    std::cerr << "lan: tail updated idx=" << idx << " rx=" << rx << std::endl;

    lan_queue_base &q = (rx ? static_cast<lan_queue_base &>(*rxqs[idx]) :
        static_cast<lan_queue_base &>(*txqs[idx]));

    if (q.is_enabled())
        q.reg_updated();
}

lan_queue_base::lan_queue_base(lan &lanmgr_, uint32_t &reg_tail_, size_t idx_,
        uint32_t &reg_ena_, uint32_t &fpm_basereg_, uint16_t ctx_size_)
    : queue_base(reg_dummy_head, reg_tail_), lanmgr(lanmgr_), enabling(false),
    idx(idx_), reg_ena(reg_ena_), fpm_basereg(fpm_basereg_),
    ctx_size(ctx_size_)
{
    ctx = new uint8_t[ctx_size_];
}

void lan_queue_base::desc_fetched(void *desc, uint32_t idx)
{
}

void lan_queue_base::data_fetched(void *desc, uint32_t idx, void *data)
{
}

void lan_queue_base::enable()
{
    if (enabling || enabled)
        return;

    std::cerr << "lan enabling queue " << idx << std::endl;
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
    std::cerr << "lan ctx fetched " << idx << std::endl;

    initialize();

    enabling = false;
    enabled = true;
    reg_ena |= I40E_QRX_ENA_QENA_STAT_MASK;

    reg_updated();
}

void lan_queue_base::disable()
{
    std::cerr << "lan disabling queue " << idx << std::endl;
    enabled = false;
    // TODO: write back
    reg_ena &= ~I40E_QRX_ENA_QENA_STAT_MASK;
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
        uint32_t &reg_ena_, uint32_t &reg_fpmbase_)
    : lan_queue_base(lanmgr_, reg_tail_, idx_, reg_ena_, reg_fpmbase_, 32)
{
}

void lan_queue_rx::initialize()
{
    std::cerr << "lan_queue_rx::initialize()" << std::endl;
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

    std::cerr << "  head=" << reg_dummy_head << " base=" << base <<
        " len=" << len << " dbsz=" << dbuff_size << " hbsz=" << hbuff_size <<
        " dtype=" << (unsigned) dtype << " longdesc=" << longdesc <<
        " crcstrip=" << crc_strip << " rxmax=" << rxmax << std::endl;
}

lan_queue_tx::lan_queue_tx(lan &lanmgr_, uint32_t &reg_tail_, size_t idx_,
        uint32_t &reg_ena_, uint32_t &reg_fpmbase_)
    : lan_queue_base(lanmgr_, reg_tail_, idx_, reg_ena_, reg_fpmbase_, 128)
{
    desc_len = 16;
}

void lan_queue_tx::initialize()
{
    std::cerr << "lan_queue_tx::initialize()" << std::endl;
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

    if (!hwb) {
        std::cerr << "    currently only hwb is supported" << std::endl;
        abort();
    }

    std::cerr << "  head=" << reg_dummy_head << " base=" << base <<
        " len=" << len << " hwb=" << hwb << " hwb_addr=" << hwb_addr <<
        std::endl;
}
