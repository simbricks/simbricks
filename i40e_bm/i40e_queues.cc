#include <stdlib.h>
#include <string.h>
#include <cassert>
#include <iostream>

#include "i40e_bm.h"

#include "i40e_base_wrapper.h"

using namespace i40e;

extern nicbm::Runner *runner;

queue_base::queue_base(uint32_t &reg_head_, uint32_t &reg_tail_)
    : base(0), len(0), fetch_head(0), reg_head(reg_head_), reg_tail(reg_tail_),
    enabled(false), desc_len(0)
{
}

void queue_base::trigger_fetch()
{
    if (fetch_head == reg_tail)
        return;


    dma_fetch *dma = new dma_fetch(*this, desc_len);
    dma->write = false;
    dma->dma_addr = base + fetch_head * desc_len;
    dma->index = fetch_head;

    std::cerr << "fetching " << (reg_tail - fetch_head) % len <<
        " descriptors from " << dma->dma_addr << std::endl;

    std::cerr << "dma = " << dma << std::endl;
    runner->issue_dma(*dma);
    fetch_head = (fetch_head + 1) % len;
}

void queue_base::reg_updated()
{
    if (!enabled)
        return;

    trigger_fetch();
}

void queue_base::desc_writeback(const void *desc, uint32_t idx)
{
    dma_wb *dma = new dma_wb(*this, desc_len);
    dma->write = true;
    dma->dma_addr = base + idx * desc_len;
    dma->index = idx;
    memcpy(dma->data, desc, desc_len);

    runner->issue_dma(*dma);
}

void queue_base::desc_written_back(uint32_t idx)
{
    std::cerr << "descriptor " << idx << " written back" << std::endl;
    reg_head = (idx + 1) % len;
}

queue_base::dma_fetch::dma_fetch(queue_base &queue_, size_t len_)
    : queue(queue_)
{
    data = new char[len_];
    len = len_;
}

queue_base::dma_fetch::~dma_fetch()
{
    delete[] ((char *) data);
}

void queue_base::dma_fetch::done()
{
    queue.desc_fetched(data, index);
    delete this;
}


queue_base::dma_wb::dma_wb(queue_base &queue_, size_t len_)
    : queue(queue_)
{
    data = new char[len_];
    len = len_;
}

queue_base::dma_wb::~dma_wb()
{
    delete[] ((char *) data);
}

void queue_base::dma_wb::done()
{
    queue.desc_written_back(index);
    queue.trigger_fetch();
    delete this;
}


/******************************************************************************/

queue_admin_tx::queue_admin_tx(i40e_bm &dev_, uint64_t &reg_base_,
        uint32_t &reg_len_, uint32_t &reg_head_, uint32_t &reg_tail_)
    : queue_base(reg_head_, reg_tail_), dev(dev_), reg_base(reg_base_),
    reg_len(reg_len_)
{
    desc_len = 32;
}

void queue_admin_tx::desc_fetched(void *desc, uint32_t idx)
{
    struct i40e_aq_desc *d = reinterpret_cast<struct i40e_aq_desc *>(desc);

    std::cerr << "descriptor " << idx << " fetched" << std::endl;

    if (d->opcode == i40e_aqc_opc_get_version) {
        std::cerr << "    get version" << std::endl;
        struct i40e_aqc_get_version *gv =
            reinterpret_cast<struct i40e_aqc_get_version *>(d->params.raw);
        gv->rom_ver = 0;
        gv->fw_build = 0;
        gv->fw_major = 0;
        gv->fw_minor = 0;
        gv->api_major = I40E_FW_API_VERSION_MAJOR;
        gv->api_minor = I40E_FW_API_VERSION_MINOR_X710;

        d->flags |= I40E_AQ_FLAG_DD | I40E_AQ_FLAG_CMP;

        desc_writeback(d, idx);
    } else if (d->opcode == i40e_aqc_opc_request_resource) {
        std::cerr << "    request resource" << std::endl;
        struct i40e_aqc_request_resource *rr =
            reinterpret_cast<struct i40e_aqc_request_resource *>(
                    d->params.raw);
        rr->timeout = 180000;
        std::cerr << "      res_id=" << rr->resource_id << std::endl;
        std::cerr << "      res_nu=" << rr->resource_number << std::endl;
    } else if (d->opcode == i40e_aqc_opc_release_resource) {
        std::cerr << "    release resource" << std::endl;
        struct i40e_aqc_request_resource *rr =
            reinterpret_cast<struct i40e_aqc_request_resource *>(
                    d->params.raw);
        std::cerr << "      res_id=" << rr->resource_id << std::endl;
        std::cerr << "      res_nu=" << rr->resource_number << std::endl;
    } else if (d->opcode == i40e_aqc_opc_clear_pxe_mode)  {
        std::cerr << "    clear PXE mode" << std::endl;
        dev.regs.gllan_rctl_0 &= ~I40E_GLLAN_RCTL_0_PXE_MODE_MASK;
    } else {
        std::cerr << "    uknown opcode=" << d->opcode << std::endl;
    }
}

void queue_admin_tx::reg_updated()
{
    base = reg_base;
    len = (reg_len & I40E_GL_ATQLEN_ATQLEN_MASK) >> I40E_GL_ATQLEN_ATQLEN_SHIFT;

    if (!enabled  && (reg_len & I40E_GL_ATQLEN_ATQENABLE_MASK)) {
        std::cerr << "enable atq base=" << base << " len=" << len << std::endl;
        enabled = true;
    } else if (enabled && !(reg_len & I40E_GL_ATQLEN_ATQENABLE_MASK)) {
        std::cerr << "disable atq" << std::endl;
        enabled = false;
    }

    queue_base::reg_updated();
}
