#include <stdlib.h>
#include <string.h>
#include <cassert>
#include <iostream>

#include "i40e_bm.h"

#include "i40e_base_wrapper.h"

nicbm::Runner *runner;

namespace i40e {

i40e_bm::i40e_bm()
    : log("i40e"),
    pf_atq(*this, regs.pf_atqba, regs.pf_atqlen, regs.pf_atqh, regs.pf_atqt),
    hmc(*this), shram(*this), lanmgr(*this, NUM_QUEUES)
{
    reset(false);
}

i40e_bm::~i40e_bm()
{
}

void i40e_bm::setup_intro(struct cosim_pcie_proto_dev_intro &di)
{
    di.bars[BAR_REGS].len = 4 * 1024 * 1024;
    di.bars[BAR_REGS].flags = COSIM_PCIE_PROTO_BAR_64;
    di.bars[BAR_IO].len = 32;
    di.bars[BAR_IO].flags = COSIM_PCIE_PROTO_BAR_IO;
    di.pci_vendor_id = I40E_INTEL_VENDOR_ID;
    di.pci_device_id = I40E_DEV_ID_QSFP_A;
    di.pci_class = 0x02;
    di.pci_subclass = 0x00;
    di.pci_revision = 0x01;
    di.pci_msi_nvecs = 32;
}

void i40e_bm::dma_complete(nicbm::DMAOp &op)
{
    dma_base &dma = dynamic_cast<dma_base &>(op);
#ifdef DEBUG_DEV
    log << "dma_complete(" << &op << ")" << logger::endl;
#endif
    dma.done();
}

void i40e_bm::eth_rx(uint8_t port, const void *data, size_t len)
{
#ifdef DEBUG_DEV
    log << "i40e: received packet len=" << len << logger::endl;
#endif
    lanmgr.packet_received(data, len);
}

void i40e_bm::reg_read(uint8_t bar, uint64_t addr, void *dest, size_t len)
{
    uint32_t *dest_p = reinterpret_cast <uint32_t *> (dest);

    if (len == 4) {
        dest_p[0] = reg_read32(bar, addr);
    } else if (len == 8) {
        dest_p[0] = reg_read32(bar, addr);
        dest_p[1] = reg_read32(bar, addr + 4);
    } else {
        log << "currently we only support 4/8B reads (got " << len << ")"
            << logger::endl;
        abort();
    }
}

uint32_t i40e_bm::reg_read32(uint8_t bar, uint64_t addr)
{
    if (bar == BAR_REGS) {
        return reg_mem_read32(addr);
    } else if (bar == BAR_IO) {
        return reg_io_read(addr);
    } else {
        log << "invalid BAR " << (int) bar << logger::endl;
        abort();
    }
}

void i40e_bm::reg_write(uint8_t bar, uint64_t addr, const void *src, size_t len)
{
    const uint32_t *src_p = reinterpret_cast<const uint32_t *> (src);

    if (len == 4) {
        reg_write32(bar, addr, src_p[0]);
    } else if (len == 8) {
        reg_write32(bar, addr, src_p[0]);
        reg_write32(bar, addr + 4, src_p[1]);
    } else {
        log << "currently we only support 4/8B writes (got " << len << ")"
            << logger::endl;
        abort();
    }
}

void i40e_bm::reg_write32(uint8_t bar, uint64_t addr, uint32_t val)
{
    if (bar == BAR_REGS) {
        reg_mem_write32(addr, val);
    } else if (bar == BAR_IO) {
        reg_io_write(addr, val);
    } else {
        log << "invalid BAR " << (int) bar << logger::endl;
        abort();
    }
}

uint32_t i40e_bm::reg_io_read(uint64_t addr)
{
    log << "unhandled io read addr="  << addr << logger::endl;
    return 0;
}

void i40e_bm::reg_io_write(uint64_t addr, uint32_t val)
{
    log << "unhandled io write addr="  << addr << " val="
        << val << logger::endl;
}

uint32_t i40e_bm::reg_mem_read32(uint64_t addr)
{
    uint32_t val = 0;

    if (addr >= I40E_PFINT_DYN_CTLN(0) &&
            addr < I40E_PFINT_DYN_CTLN(NUM_PFINTS - 1))
    {
        val = regs.pfint_dyn_ctln[(addr - I40E_PFINT_DYN_CTLN(0)) / 4];
    } else if (addr >= I40E_PFINT_LNKLSTN(0) &&
            addr <= I40E_PFINT_LNKLSTN(NUM_PFINTS - 1))
    {
        val = regs.pfint_lnklstn[(addr - I40E_PFINT_LNKLSTN(0)) / 4];
    } else if (addr >= I40E_PFINT_RATEN(0) &&
            addr <= I40E_PFINT_RATEN(NUM_PFINTS - 1))
    {
        val = regs.pfint_raten[(addr - I40E_PFINT_RATEN(0)) / 4];

    } else if (addr >= I40E_GLLAN_TXPRE_QDIS(0) &&
            addr < I40E_GLLAN_TXPRE_QDIS(12))
    {
        val = regs.gllan_txpre_qdis[(addr - I40E_GLLAN_TXPRE_QDIS(0)) / 4];
    } else if (addr >= I40E_QINT_TQCTL(0) &&
            addr <= I40E_QINT_TQCTL(NUM_QUEUES - 1))
    {
        val = regs.qint_tqctl[(addr - I40E_QINT_TQCTL(0)) / 4];
    } else if (addr >= I40E_QTX_ENA(0) &&
            addr <= I40E_QTX_ENA(NUM_QUEUES - 1))
    {
        val = regs.qtx_ena[(addr - I40E_QTX_ENA(0)) / 4];
    } else if (addr >= I40E_QTX_TAIL(0) &&
            addr <= I40E_QTX_TAIL(NUM_QUEUES - 1))
    {
        val = regs.qtx_tail[(addr - I40E_QTX_TAIL(0)) / 4];
    } else if (addr >= I40E_QINT_RQCTL(0) &&
            addr <= I40E_QINT_RQCTL(NUM_QUEUES - 1))
    {
        val = regs.qint_rqctl[(addr - I40E_QINT_RQCTL(0)) / 4];
    } else if (addr >= I40E_QRX_ENA(0) &&
            addr <= I40E_QRX_ENA(NUM_QUEUES - 1))
    {
        val = regs.qrx_ena[(addr - I40E_QRX_ENA(0)) / 4];
    } else if (addr >= I40E_QRX_TAIL(0) &&
            addr <= I40E_QRX_TAIL(NUM_QUEUES - 1))
    {
        val = regs.qrx_tail[(addr - I40E_QRX_TAIL(0)) / 4];
    } else if (addr >= I40E_GLHMC_LANTXBASE(0) &&
            addr <= I40E_GLHMC_LANTXBASE(I40E_GLHMC_LANTXBASE_MAX_INDEX))
    {
        val = regs.glhmc_lantxbase[(addr - I40E_GLHMC_LANTXBASE(0)) / 4];
    } else if (addr >= I40E_GLHMC_LANTXCNT(0) &&
            addr <= I40E_GLHMC_LANTXCNT(I40E_GLHMC_LANTXCNT_MAX_INDEX))
    {
        val = regs.glhmc_lantxcnt[(addr - I40E_GLHMC_LANTXCNT(0)) / 4];
    } else if (addr >= I40E_GLHMC_LANRXBASE(0) &&
            addr <= I40E_GLHMC_LANRXBASE(I40E_GLHMC_LANRXBASE_MAX_INDEX))
    {
        val = regs.glhmc_lanrxbase[(addr - I40E_GLHMC_LANRXBASE(0)) / 4];
    } else if (addr >= I40E_GLHMC_LANRXCNT(0) &&
            addr <= I40E_GLHMC_LANRXCNT(I40E_GLHMC_LANRXCNT_MAX_INDEX))
    {
        val = regs.glhmc_lanrxcnt[(addr - I40E_GLHMC_LANRXCNT(0)) / 4];
    } else if (addr >= I40E_GLQF_HKEY(0) &&
            addr <= I40E_GLQF_HKEY(I40E_GLQF_HKEY_MAX_INDEX))
    {
        val = regs.glqf_hkey[(addr - I40E_GLQF_HKEY(0)) / 4];
    } else {

        switch (addr) {
            case I40E_PFGEN_CTRL:
                val = 0; /* we always simulate immediate reset */
                break;

            case I40E_GL_FWSTS:
                val = 0;
                break;

            case I40E_GLPCI_CAPSUP:
                val = 0;
                break;

            case I40E_GLNVM_ULD:
                val = 0xffffffff;
                break;

            case I40E_GLNVM_GENS:
                val = I40E_GLNVM_GENS_NVM_PRES_MASK |
                    (6 << I40E_GLNVM_GENS_SR_SIZE_SHIFT); // shadow ram 64kb
                break;

            case I40E_GLNVM_FLA:
                val = I40E_GLNVM_FLA_LOCKED_MASK; /* normal flash programming
                                                     mode */
                break;

            case I40E_GLGEN_RSTCTL:
                val = regs.glgen_rstctl;
                break;
            case I40E_GLGEN_STAT:
                val = regs.glgen_stat;
                break;

            case I40E_GLVFGEN_TIMER:
                val = runner->time_ps() / 1000000;
                break;

            case I40E_PFINT_LNKLST0:
                val = regs.pfint_lnklst0;
                break;

            case I40E_PFINT_ICR0_ENA:
                val = regs.pfint_icr0_ena;
                break;

            case I40E_PFINT_ICR0:
                val = regs.pfint_icr0;
                // read clears
                regs.pfint_icr0 = 0;
                break;

            case I40E_PFINT_DYN_CTL0:
                val = regs.pfint_dyn_ctl0;
                break;

            case I40E_PFINT_ITR0(0):
                val = regs.pfint_itr0[0];
                break;
            case I40E_PFINT_ITR0(1):
                val = regs.pfint_itr0[1];
                break;
            case I40E_PFINT_ITR0(2):
                val = regs.pfint_itr0[2];
                break;

            case I40E_GLPCI_CNF2:
                val = ((NUM_PFINTS - 2) << I40E_GLPCI_CNF2_MSI_X_PF_N_SHIFT) |
                    (2 << I40E_GLPCI_CNF2_MSI_X_VF_N_SHIFT); /* that is ugly,
                                                                but linux
                                                                driver needs
                                                                this not to
                                                                crash. */
                break;

            case I40E_GLNVM_SRCTL:
                val = regs.glnvm_srctl;
                break;
            case I40E_GLNVM_SRDATA:
                val = regs.glnvm_srdata;
                break;

            case I40E_PFLAN_QALLOC:
                val = (0 << I40E_PFLAN_QALLOC_FIRSTQ_SHIFT) |
                    ((NUM_QUEUES - 1) << I40E_PFLAN_QALLOC_LASTQ_SHIFT) |
                    (1 << I40E_PFLAN_QALLOC_VALID_SHIFT);
                break;

            case I40E_PF_VT_PFALLOC:
                val = 0; // we don't currently support VFs
                break;

            case I40E_PFGEN_PORTNUM:
                val = (0 << I40E_PFGEN_PORTNUM_PORT_NUM_SHIFT);
                break;

            case I40E_GLLAN_RCTL_0:
                val = regs.gllan_rctl_0;
                break;


            case I40E_GLHMC_LANTXOBJSZ:
                val = 7; // 128 B
                break;

            case I40E_GLHMC_LANQMAX:
                val = NUM_QUEUES;
                break;
            case I40E_GLHMC_LANRXOBJSZ:
                val = 5; // 32 B
                break;

            case I40E_GLHMC_FCOEMAX:
                val = 0;
                break;
            case I40E_GLHMC_FCOEDDPOBJSZ:
                val = 0;
                break;
            case I40E_GLHMC_FCOEFMAX:
                // needed to make linux driver happy
                val = 0x1000 << I40E_GLHMC_FCOEFMAX_PMFCOEFMAX_SHIFT;
                break;
            case I40E_GLHMC_FCOEFOBJSZ:
                val = 0;
                break;

            case I40E_PFHMC_SDCMD:
                val = regs.pfhmc_sdcmd;
                break;
            case I40E_PFHMC_SDDATALOW:
                val = regs.pfhmc_sddatalow;
                break;
            case I40E_PFHMC_SDDATAHIGH:
                val = regs.pfhmc_sddatahigh;
                break;
            case I40E_PFHMC_PDINV:
                val = regs.pfhmc_pdinv;
                break;
            case I40E_PFHMC_ERRORINFO:
                val = regs.pfhmc_errorinfo;
                break;
            case I40E_PFHMC_ERRORDATA:
                val = regs.pfhmc_errordata;
                break;

            case I40E_PF_ATQBAL:
                val = regs.pf_atqba;
                break;
            case I40E_PF_ATQBAH:
                val = regs.pf_atqba >> 32;
                break;
            case I40E_PF_ATQLEN:
                val = regs.pf_atqlen;
                break;
            case I40E_PF_ATQH:
                val = regs.pf_atqh;
                break;
            case I40E_PF_ATQT:
                val = regs.pf_atqt;
                break;

            case I40E_PF_ARQBAL:
                val = regs.pf_arqba;
                break;
            case I40E_PF_ARQBAH:
                val = regs.pf_arqba >> 32;
                break;
            case I40E_PF_ARQLEN:
                val = regs.pf_arqlen;
                break;
            case I40E_PF_ARQH:
                val = regs.pf_arqh;
                break;
            case I40E_PF_ARQT:
                val = regs.pf_arqt;
                break;

            case I40E_PRTMAC_LINKSTA:
                val = I40E_REG_LINK_UP | I40E_REG_SPEED_25_40GB;
                break;

            case I40E_PRTMAC_MACC:
                val = 0;
                break;

            default:
#ifdef DEBUG_DEV
                log << "unhandled mem read addr="  << addr
                    << logger::endl;
#endif
                break;
        }
    }

    return val;
}

void i40e_bm::reg_mem_write32(uint64_t addr, uint32_t val)
{
    if (addr >= I40E_PFINT_DYN_CTLN(0) &&
            addr <= I40E_PFINT_DYN_CTLN(NUM_PFINTS - 1))
    {
        regs.pfint_dyn_ctln[(addr - I40E_PFINT_DYN_CTLN(0)) / 4] = val;
    } else if (addr >= I40E_PFINT_LNKLSTN(0) &&
            addr <= I40E_PFINT_LNKLSTN(NUM_PFINTS - 1))
    {
        regs.pfint_lnklstn[(addr - I40E_PFINT_LNKLSTN(0)) / 4] = val;
    } else if (addr >= I40E_PFINT_RATEN(0) &&
            addr <= I40E_PFINT_RATEN(NUM_PFINTS - 1))
    {
        regs.pfint_raten[(addr - I40E_PFINT_RATEN(0)) / 4] = val;
    } else if (addr >= I40E_GLLAN_TXPRE_QDIS(0) &&
            addr <= I40E_GLLAN_TXPRE_QDIS(11))
    {
        regs.gllan_txpre_qdis[(addr - I40E_GLLAN_TXPRE_QDIS(0)) / 4] = val;
    } else if (addr >= I40E_QINT_TQCTL(0) &&
            addr <= I40E_QINT_TQCTL(NUM_QUEUES - 1))
    {
        regs.qint_tqctl[(addr - I40E_QINT_TQCTL(0)) / 4] = val;
    } else if (addr >= I40E_QTX_ENA(0) &&
            addr <= I40E_QTX_ENA(NUM_QUEUES - 1))
    {
        size_t idx = (addr - I40E_QTX_ENA(0)) / 4;
        regs.qtx_ena[idx] = val;
        lanmgr.qena_updated(idx, false);
    } else if (addr >= I40E_QTX_TAIL(0) &&
            addr <= I40E_QTX_TAIL(NUM_QUEUES - 1))
    {
        size_t idx = (addr - I40E_QTX_TAIL(0)) / 4;
        regs.qtx_tail[idx] = val;
        lanmgr.tail_updated(idx, false);
    } else if (addr >= I40E_QINT_RQCTL(0) &&
            addr <= I40E_QINT_RQCTL(NUM_QUEUES - 1))
    {
        regs.qint_rqctl[(addr - I40E_QINT_RQCTL(0)) / 4] = val;
    } else if (addr >= I40E_QRX_ENA(0) &&
            addr <= I40E_QRX_ENA(NUM_QUEUES - 1))
    {
        size_t idx = (addr - I40E_QRX_ENA(0)) / 4;
        regs.qrx_ena[idx] = val;
        lanmgr.qena_updated(idx, true);
    } else if (addr >= I40E_QRX_TAIL(0) &&
            addr <= I40E_QRX_TAIL(NUM_QUEUES - 1))
    {
        size_t idx = (addr - I40E_QRX_TAIL(0)) / 4;
        regs.qrx_tail[idx] = val;
        lanmgr.tail_updated(idx, true);
    } else if (addr >= I40E_GLHMC_LANTXBASE(0) &&
            addr <= I40E_GLHMC_LANTXBASE(I40E_GLHMC_LANTXBASE_MAX_INDEX))
    {
        regs.glhmc_lantxbase[(addr - I40E_GLHMC_LANTXBASE(0)) / 4] = val;
    } else if (addr >= I40E_GLHMC_LANTXCNT(0) &&
            addr <= I40E_GLHMC_LANTXCNT(I40E_GLHMC_LANTXCNT_MAX_INDEX))
    {
        regs.glhmc_lantxcnt[(addr - I40E_GLHMC_LANTXCNT(0)) / 4] = val;
    } else if (addr >= I40E_GLHMC_LANRXBASE(0) &&
            addr <= I40E_GLHMC_LANRXBASE(I40E_GLHMC_LANRXBASE_MAX_INDEX))
    {
        regs.glhmc_lanrxbase[(addr - I40E_GLHMC_LANRXBASE(0)) / 4] = val;
    } else if (addr >= I40E_GLHMC_LANRXCNT(0) &&
            addr <= I40E_GLHMC_LANRXCNT(I40E_GLHMC_LANRXCNT_MAX_INDEX))
    {
        regs.glhmc_lanrxcnt[(addr - I40E_GLHMC_LANRXCNT(0)) / 4] = val;
    } else if (addr >= I40E_GLQF_HKEY(0) &&
            addr <= I40E_GLQF_HKEY(I40E_GLQF_HKEY_MAX_INDEX))
    {
        regs.glqf_hkey[(addr - I40E_GLQF_HKEY(0)) / 4] = val;
    } else {
        switch (addr) {
            case I40E_PFGEN_CTRL:
                if ((val & I40E_PFGEN_CTRL_PFSWR_MASK) ==
                        I40E_PFGEN_CTRL_PFSWR_MASK)
                    reset(true);
                break;

            case I40E_GL_FWSTS:
                break;

            case I40E_GLGEN_RSTCTL:
                regs.glgen_rstctl = val;
                break;

            case I40E_GLLAN_RCTL_0:
                if ((val & I40E_GLLAN_RCTL_0_PXE_MODE_MASK))
                    regs.gllan_rctl_0 &= ~I40E_GLLAN_RCTL_0_PXE_MODE_MASK;
                break;

            case I40E_GLNVM_SRCTL:
                regs.glnvm_srctl = val;
                shram.reg_updated();
                break;
            case I40E_GLNVM_SRDATA:
                regs.glnvm_srdata = val;
                shram.reg_updated();
                break;

            case I40E_PFINT_LNKLST0:
                regs.pfint_lnklst0 = val;
                break;

            case I40E_PFINT_ICR0_ENA:
                regs.pfint_icr0_ena = val;
                break;
            case I40E_PFINT_ICR0:
                regs.pfint_icr0 = val;
                break;
            case I40E_PFINT_DYN_CTL0:
                regs.pfint_dyn_ctl0 = val;
                break;
            case I40E_PFINT_ITR0(0):
                regs.pfint_itr0[0] = val;
                break;
            case I40E_PFINT_ITR0(1):
                regs.pfint_itr0[1] = val;
                break;
            case I40E_PFINT_ITR0(2):
                regs.pfint_itr0[2] = val;
                break;

            case I40E_PFHMC_SDCMD:
                regs.pfhmc_sdcmd = val;
                hmc.reg_updated(addr);
                break;
            case I40E_PFHMC_SDDATALOW:
                regs.pfhmc_sddatalow = val;
                hmc.reg_updated(addr);
                break;
            case I40E_PFHMC_SDDATAHIGH:
                regs.pfhmc_sddatahigh = val;
                hmc.reg_updated(addr);
                break;
            case I40E_PFHMC_PDINV:
                regs.pfhmc_pdinv = val;
                hmc.reg_updated(addr);
                break;

            case I40E_PF_ATQBAL:
                regs.pf_atqba = val | (regs.pf_atqba & 0xffffffff00000000ULL);
                pf_atq.reg_updated();
                break;
            case I40E_PF_ATQBAH:
                regs.pf_atqba = ((uint64_t ) val << 32) |
                    (regs.pf_atqba & 0xffffffffULL);
                pf_atq.reg_updated();
                break;
            case I40E_PF_ATQLEN:
                regs.pf_atqlen = val;
                pf_atq.reg_updated();
                break;
            case I40E_PF_ATQH:
                regs.pf_atqh = val;
                pf_atq.reg_updated();
                break;
            case I40E_PF_ATQT:
                regs.pf_atqt = val;
                pf_atq.reg_updated();
                break;

            case I40E_PF_ARQBAL:
                regs.pf_arqba = val | (regs.pf_atqba & 0xffffffff00000000ULL);
                break;
            case I40E_PF_ARQBAH:
                regs.pf_arqba = ((uint64_t ) val << 32) |
                    (regs.pf_arqba & 0xffffffffULL);
                break;
            case I40E_PF_ARQLEN:
                regs.pf_arqlen = val;
                break;
            case I40E_PF_ARQH:
                regs.pf_arqh = val;
                break;
            case I40E_PF_ARQT:
                regs.pf_arqt = val;
                break;

            default:
#ifdef DEBUG_DEV
                log << "unhandled mem write addr="  << addr
                    << " val=" << val << logger::endl;
#endif
                break;
        }
    }
}

void i40e_bm::timed_event(nicbm::TimedEvent &ev)
{
    int_ev &iev = *((int_ev *) &ev);
#ifdef DEBUG_DEV
    log << "timed_event: triggering interrupt (" << iev.vector << ")" <<
        logger::endl;
#endif
    iev.armed = false;
    runner->msi_issue(0);
}

void i40e_bm::signal_interrupt(uint16_t vector, uint8_t itr)
{
    if (vector != 0) {
        log << "signal_interrupt() only supports vector 0" << logger::endl;
        abort();
    }

    int_ev &iev = intevs[vector];

    uint64_t mindelay;
    if (itr <= 2) {
        // itr 0-2
        mindelay = regs.pfint_itr0[itr];
        mindelay *= 2000000ULL;
    } else if (itr == 3) {
        // noitr
        mindelay = 0;
    } else {
        log << "signal_interrupt() invalid itr (" << itr << ")" << logger::endl;
        abort();
    }

    uint64_t curtime = runner->time_ps();
    uint64_t newtime = curtime + mindelay;
    if (iev.armed && iev.time <= newtime) {
        // already armed and this is not scheduled sooner
#ifdef DEBUG_DEV
        log << "signal_interrupt: vector " << vector << " already scheduled" <<
            logger::endl;
#endif
        return;
    } else if (iev.armed) {
        // need to reschedule
        runner->event_cancel(iev);
    }

    iev.armed = true;
    iev.time = newtime;

#ifdef DEBUG_DEV
    log << "signal_interrupt: scheduled vector " << vector << " for time=" <<
        newtime << " (itr " << itr << ")" << logger::endl;
#endif

    runner->event_schedule(iev);
}

void i40e_bm::reset(bool indicate_done)
{
#ifdef DEBUG_DEV
    std::cout << "reset triggered" << logger::endl;
#endif

    pf_atq.reset();
    hmc.reset();
    lanmgr.reset();

    memset(&regs, 0, sizeof(regs));
    if (indicate_done)
        regs.glnvm_srctl = I40E_GLNVM_SRCTL_DONE_MASK;

    for (uint16_t i = 0; i < NUM_PFINTS; i++) {
        intevs[i].vector = i;
        if (intevs[i].armed) {
            runner->event_cancel(intevs[i]);
            intevs[i].armed = false;
        }
        intevs[i].time = 0;
    }
}

shadow_ram::shadow_ram(i40e_bm &dev_)
    : dev(dev_), log("sram")
{
}

void shadow_ram::reg_updated()
{
    uint32_t val = dev.regs.glnvm_srctl;
    uint32_t addr;
    bool is_write;

    if (!(val & I40E_GLNVM_SRCTL_START_MASK))
        return;

    addr = (val & I40E_GLNVM_SRCTL_ADDR_MASK)
        >> I40E_GLNVM_SRCTL_ADDR_SHIFT;
    is_write = (val & I40E_GLNVM_SRCTL_WRITE_MASK);

#ifdef DEBUG_DEV
    log << "shadow ram op addr="  << addr << " w=" << is_write
        << logger::endl;
#endif

    if (is_write) {
        write(addr,
                (dev.regs.glnvm_srdata & I40E_GLNVM_SRDATA_WRDATA_MASK)
                >> I40E_GLNVM_SRDATA_WRDATA_SHIFT);
    } else {
        dev.regs.glnvm_srdata &= ~I40E_GLNVM_SRDATA_RDDATA_MASK;
        dev.regs.glnvm_srdata |= ((uint32_t) read(addr)) <<
            I40E_GLNVM_SRDATA_RDDATA_SHIFT;
    }

    dev.regs.glnvm_srctl &= ~I40E_GLNVM_SRCTL_START_MASK;
    dev.regs.glnvm_srctl |= I40E_GLNVM_SRCTL_DONE_MASK;
}

uint16_t shadow_ram::read(uint16_t addr)
{
    switch (addr) {
        /* for any of these hopefully return 0 should be fine */
        /* they are read by drivers but not used */
        case I40E_SR_NVM_DEV_STARTER_VERSION:
        case I40E_SR_NVM_EETRACK_LO:
        case I40E_SR_NVM_EETRACK_HI:
        case I40E_SR_BOOT_CONFIG_PTR:
             return 0;

        case I40E_SR_NVM_CONTROL_WORD:
             return (1 << I40E_SR_CONTROL_WORD_1_SHIFT);

        case I40E_SR_SW_CHECKSUM_WORD:
             return 0xbaba;

        default:
#ifdef DEBUG_DEV
             log << "TODO shadow memory read addr="  << addr
                 << logger::endl;
#endif
             break;
    }

    return 0;
}

void shadow_ram::write(uint16_t addr, uint16_t val)
{
#ifdef DEBUG_DEV
    log << "TODO shadow memory write addr="  << addr <<
        " val=" << val << logger::endl;
#endif
}

int_ev::int_ev()
{
    armed = false;
    time = 0;
}

} //namespace i40e

using namespace i40e;

int main(int argc, char *argv[])
{
    i40e_bm dev;
    runner = new nicbm::Runner(dev);
    return runner->runMain(argc, argv);
}
