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

#include <stdlib.h>
#include <string.h>

#include <algorithm>
#include <cassert>
#include <iostream>

#include "sims/nic/i40e_bm/i40e_base_wrapper.h"
#include "sims/nic/i40e_bm/i40e_bm.h"

using namespace i40e;

extern nicbm::Runner *runner;

queue_base::queue_base(const std::string &qname_, uint32_t &reg_head_,
                       uint32_t &reg_tail_)
    : qname(qname_),
      log(qname_),
      active_first_pos(0),
      active_first_idx(0),
      active_cnt(0),
      base(0),
      len(0),
      reg_head(reg_head_),
      reg_tail(reg_tail_),
      enabled(false),
      desc_len(0) {
  for (size_t i = 0; i < MAX_ACTIVE_DESCS; i++) {
    desc_ctxs[i] = nullptr;
  }
}

void queue_base::ctxs_init() {
  for (size_t i = 0; i < MAX_ACTIVE_DESCS; i++) {
    desc_ctxs[i] = &desc_ctx_create();
  }
}

void queue_base::trigger_fetch() {
  if (!enabled)
    return;

  // calculate how many we can fetch
  uint32_t next_idx = (active_first_idx + active_cnt) % len;
  uint32_t desc_avail = (reg_tail - next_idx) % len;
  uint32_t fetch_cnt = desc_avail;
  fetch_cnt = std::min(fetch_cnt, MAX_ACTIVE_DESCS - active_cnt);
  if (max_active_capacity() <= active_cnt)
    fetch_cnt = std::min(fetch_cnt, max_active_capacity() - active_cnt);
  fetch_cnt = std::min(fetch_cnt, max_fetch_capacity());

  if (next_idx + fetch_cnt > len)
    fetch_cnt = len - next_idx;

#ifdef DEBUG_QUEUES
  log << "fetching avail=" << desc_avail << " cnt=" << fetch_cnt
      << " idx=" << next_idx << logger::endl;
#endif

  // abort if nothign to fetch
  if (fetch_cnt == 0)
    return;

  // mark descriptor contexts as fetching
  uint32_t first_pos = (active_first_pos + active_cnt) % MAX_ACTIVE_DESCS;
  for (uint32_t i = 0; i < fetch_cnt; i++) {
    desc_ctx &ctx = *desc_ctxs[(first_pos + i) % MAX_ACTIVE_DESCS];
    assert(ctx.state == desc_ctx::DESC_EMPTY);

    ctx.state = desc_ctx::DESC_FETCHING;
    ctx.index = (next_idx + i) % len;
  }
  active_cnt += fetch_cnt;

  // prepare & issue dma
  dma_fetch *dma = new dma_fetch(*this, desc_len * fetch_cnt);
  dma->write_ = false;
  dma->dma_addr_ = base + next_idx * desc_len;
  dma->pos = first_pos;
#ifdef DEBUG_QUEUES
  log << "    dma = " << dma << logger::endl;
#endif
  runner->IssueDma(*dma);
}

void queue_base::trigger_process() {
  if (!enabled)
    return;

  // first skip over descriptors that are already done processing
  uint32_t i;
  for (i = 0; i < active_cnt; i++)
    if (desc_ctxs[(active_first_pos + i) % MAX_ACTIVE_DESCS]->state <=
        desc_ctx::DESC_PREPARED)
      break;

  // then run all prepared contexts
  uint32_t j;
  for (j = 0; i + j < active_cnt; j++) {
    desc_ctx &ctx = *desc_ctxs[(active_first_pos + i + j) % MAX_ACTIVE_DESCS];
    if (ctx.state != desc_ctx::DESC_PREPARED)
      break;

    ctx.state = desc_ctx::DESC_PROCESSING;
#ifdef DEBUG_QUEUES
    log << "processing desc " << ctx.index << logger::endl;
#endif
    ctx.process();
  }
}

void queue_base::trigger_writeback() {
  if (!enabled)
    return;

  // from first pos count number of processed descriptors
  uint32_t avail;
  for (avail = 0; avail < active_cnt; avail++)
    if (desc_ctxs[(active_first_pos + avail) % MAX_ACTIVE_DESCS]->state !=
        desc_ctx::DESC_PROCESSED)
      break;

  uint32_t cnt = std::min(avail, max_writeback_capacity());
  if (active_first_idx + cnt > len)
    cnt = len - active_first_idx;

#ifdef DEBUG_QUEUES
  log << "writing back avail=" << avail << " cnt=" << cnt
      << " idx=" << active_first_idx << logger::endl;
#endif

  if (cnt == 0)
    return;

  // mark these descriptors as writing back
  for (uint32_t i = 0; i < cnt; i++) {
    desc_ctx &ctx = *desc_ctxs[(active_first_pos + i) % MAX_ACTIVE_DESCS];
    ctx.state = desc_ctx::DESC_WRITING_BACK;
  }

  do_writeback(active_first_idx, active_first_pos, cnt);
}

void queue_base::trigger() {
  trigger_fetch();
  trigger_process();
  trigger_writeback();
}

void queue_base::reset() {
#ifdef DEBUG_QUEUES
  log << "reset" << logger::endl;
#endif

  enabled = false;
  active_first_pos = 0;
  active_first_idx = 0;
  active_cnt = 0;

  for (size_t i = 0; i < MAX_ACTIVE_DESCS; i++) {
    desc_ctxs[i]->state = desc_ctx::DESC_EMPTY;
  }
}

void queue_base::reg_updated() {
#ifdef DEBUG_QUEUES
  log << "reg_updated: tail=" << reg_tail << " enabled=" << (int)enabled
      << logger::endl;
#endif
  if (!enabled)
    return;

  trigger();
}

bool queue_base::is_enabled() {
  return enabled;
}

uint32_t queue_base::max_fetch_capacity() {
  return UINT32_MAX;
}

uint32_t queue_base::max_active_capacity() {
  return UINT32_MAX;
}

uint32_t queue_base::max_writeback_capacity() {
  return UINT32_MAX;
}

void queue_base::interrupt() {
}

void queue_base::do_writeback(uint32_t first_idx, uint32_t first_pos,
                              uint32_t cnt) {
  dma_wb *dma = new dma_wb(*this, desc_len * cnt);
  dma->write_ = true;
  dma->dma_addr_ = base + first_idx * desc_len;
  dma->pos = first_pos;

  uint8_t *buf = reinterpret_cast<uint8_t *>(dma->data_);
  for (uint32_t i = 0; i < cnt; i++) {
    desc_ctx &ctx = *desc_ctxs[(first_pos + i) % MAX_ACTIVE_DESCS];
    assert(ctx.state == desc_ctx::DESC_WRITING_BACK);
    memcpy(buf + i * desc_len, ctx.desc, desc_len);
  }

  runner->IssueDma(*dma);
}

void queue_base::writeback_done(uint32_t first_pos, uint32_t cnt) {
  if (!enabled)
    return;

  // first mark descriptors as written back
  for (uint32_t i = 0; i < cnt; i++) {
    desc_ctx &ctx = *desc_ctxs[(first_pos + i) % MAX_ACTIVE_DESCS];
    assert(ctx.state == desc_ctx::DESC_WRITING_BACK);
    ctx.state = desc_ctx::DESC_WRITTEN_BACK;
  }

#ifdef DEBUG_QUEUES
  log << "written back afi=" << active_first_idx << " afp=" << active_first_pos
      << " acnt=" << active_cnt << " pos=" << first_pos << " cnt=" << cnt
      << logger::endl;
#endif

  // then start at the beginning and check how many are written back and then
  // free those
  uint32_t bump_cnt = 0;
  for (bump_cnt = 0; bump_cnt < active_cnt; bump_cnt++) {
    desc_ctx &ctx =
        *desc_ctxs[(active_first_pos + bump_cnt) % MAX_ACTIVE_DESCS];
    if (ctx.state != desc_ctx::DESC_WRITTEN_BACK)
      break;

    ctx.state = desc_ctx::DESC_EMPTY;
  }
#ifdef DEBUG_QUEUES
  log << "   bump_cnt=" << bump_cnt << logger::endl;
#endif

  active_first_pos = (active_first_pos + bump_cnt) % MAX_ACTIVE_DESCS;
  active_first_idx = (active_first_idx + bump_cnt) % len;
  active_cnt -= bump_cnt;

  reg_head = active_first_idx;
  interrupt();
}

queue_base::desc_ctx::desc_ctx(queue_base &queue_)
    : queue(queue_),
      state(DESC_EMPTY),
      index(0),
      data(nullptr),
      data_len(0),
      data_capacity(0) {
  desc = new uint8_t[queue_.desc_len];
}

queue_base::desc_ctx::~desc_ctx() {
  delete[]((uint8_t *)desc);
  if (data_capacity > 0)
    delete[]((uint8_t *)data);
}

void queue_base::desc_ctx::prepare() {
  prepared();
}

void queue_base::desc_ctx::prepared() {
#ifdef DEBUG_QUEUES
  queue.log << "prepared desc " << index << logger::endl;
#endif
  assert(state == DESC_PREPARING);
  state = DESC_PREPARED;
}

void queue_base::desc_ctx::processed() {
#ifdef DEBUG_QUEUES
  queue.log << "processed desc " << index << logger::endl;
#endif
  assert(state == DESC_PROCESSING);
  state = DESC_PROCESSED;
}

#define MAX_DMA_SIZE ((size_t)9024)

void queue_base::desc_ctx::data_fetch(uint64_t addr, size_t data_len) {
  if (data_capacity < data_len) {
#ifdef DEBUG_QUEUES
    queue.log << "data_fetch allocating" << logger::endl;
#endif
    if (data_capacity != 0)
      delete[]((uint8_t *)data);

    data = new uint8_t[data_len];
    data_capacity = data_len;
  }

  dma_data_fetch *dma =
      new dma_data_fetch(*this, std::min(data_len, MAX_DMA_SIZE), data);
  dma->part_offset = 0;
  dma->total_len = data_len;
  dma->write_ = false;
  dma->dma_addr_ = addr;

#ifdef DEBUG_QUEUES
  queue.log << "fetching data idx=" << index << " addr=" << addr
            << " len=" << data_len << logger::endl;
  queue.log << "  dma = " << dma << " data=" << data << logger::endl;
#endif
  runner->IssueDma(*dma);
}

void queue_base::desc_ctx::data_fetched(uint64_t addr, size_t len) {
  prepared();
}

void queue_base::desc_ctx::data_write(uint64_t addr, size_t data_len,
                                      const void *buf) {
#ifdef DEBUG_QUEUES
  queue.log << "data_write(addr=" << addr << " datalen=" << data_len << ")"
            << logger::endl;
#endif
  dma_data_wb *data_dma = new dma_data_wb(*this, data_len);
  data_dma->write_ = true;
  data_dma->dma_addr_ = addr;
  memcpy(data_dma->data_, buf, data_len);

  runner->IssueDma(*data_dma);
}

void queue_base::desc_ctx::data_written(uint64_t addr, size_t len) {
#ifdef DEBUG_QUEUES
  queue.log << "data_written(addr=" << addr << " datalen=" << len << ")"
            << logger::endl;
#endif
  processed();
}

queue_base::dma_fetch::dma_fetch(queue_base &queue_, size_t len)
    : queue(queue_) {
  data_ = new char[len];
  len_ = len;
}

queue_base::dma_fetch::~dma_fetch() {
  delete[]((char *)data_);
}

void queue_base::dma_fetch::done() {
  uint8_t *buf = reinterpret_cast<uint8_t *>(data_);
  for (uint32_t i = 0; i < len_ / queue.desc_len; i++) {
    desc_ctx &ctx = *queue.desc_ctxs[(pos + i) % queue.MAX_ACTIVE_DESCS];
    memcpy(ctx.desc, buf + queue.desc_len * i, queue.desc_len);

#ifdef DEBUG_QUEUES
    queue.log << "preparing desc " << ctx.index << logger::endl;
#endif
    ctx.state = desc_ctx::DESC_PREPARING;
    ctx.prepare();
  }
  queue.trigger();
  delete this;
}

queue_base::dma_data_fetch::dma_data_fetch(desc_ctx &ctx_, size_t len,
                                           void *buffer)
    : ctx(ctx_) {
  data_ = buffer;
  len_ = len;
}

queue_base::dma_data_fetch::~dma_data_fetch() {
}

void queue_base::dma_data_fetch::done() {
  part_offset += len_;
  dma_addr_ += len_;
  data_ = (uint8_t *)data_ + len_;

  if (part_offset < total_len) {
#ifdef DEBUG_QUEUES
    ctx.queue.log << "  dma_fetch: next part of multi part dma" << logger::endl;
#endif
    len_ = std::min(total_len - part_offset, MAX_DMA_SIZE);
    runner->IssueDma(*this);
    return;
  }
  ctx.data_fetched(dma_addr_ - part_offset, total_len);
  ctx.queue.trigger();
  delete this;
}

queue_base::dma_wb::dma_wb(queue_base &queue_, size_t len) : queue(queue_) {
  data_ = new char[len];
  len_ = len;
}

queue_base::dma_wb::~dma_wb() {
  delete[]((char *)data_);
}

void queue_base::dma_wb::done() {
  queue.writeback_done(pos, len_ / queue.desc_len);
  queue.trigger();
  delete this;
}

queue_base::dma_data_wb::dma_data_wb(desc_ctx &ctx_, size_t len) : ctx(ctx_) {
  data_ = new char[len];
  len_ = len;
}

queue_base::dma_data_wb::~dma_data_wb() {
  delete[]((char *)data_);
}

void queue_base::dma_data_wb::done() {
  ctx.data_written(dma_addr_, len_);
  ctx.queue.trigger();
  delete this;
}
