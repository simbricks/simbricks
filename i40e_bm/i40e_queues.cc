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

void queue_base::desc_writeback_indirect(const void *desc, uint32_t idx,
        uint64_t data_addr, const void *data, size_t data_len)
{
    // descriptor dma
    dma_wb *desc_dma = new dma_wb(*this, desc_len);
    desc_dma->write = true;
    desc_dma->dma_addr = base + idx * desc_len;
    desc_dma->index = idx;
    memcpy(desc_dma->data, desc, desc_len);
    // purposefully not issued yet, data dma will issue once ready

    // data dma
    dma_data_wb *data_dma = new dma_data_wb(*this, data_len, *desc_dma);
    data_dma->write = true;
    data_dma->dma_addr = data_addr;
    data_dma->index = idx;
    memcpy(data_dma->data, data, data_len);

    runner->issue_dma(*data_dma);
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


queue_base::dma_data_wb::dma_data_wb(queue_base &queue_, size_t len_,
        dma_wb &desc_dma_)
    : queue(queue_), desc_dma(desc_dma_)
{
    data = new char[len_];
    len = len_;
}

queue_base::dma_data_wb::~dma_data_wb()
{
    delete[] ((char *) data);
}

void queue_base::dma_data_wb::done()
{
    // now we can issue descriptor dma
    runner->issue_dma(desc_dma);
    delete this;
}