/*
 * Copyright 2024 Max Planck Institute for Software Systems, and
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
#ifndef SIMBRICKS_AXI_AXI_SUBORDINATE_HH_
#define SIMBRICKS_AXI_AXI_SUBORDINATE_HH_

#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <deque>
#include <iostream>
#include <memory>
#include <optional>
#include <unordered_map>

// #define AXI_R_DEBUG 0
// #define AXI_W_DEBUG 0

namespace simbricks {
struct AXIOperation {
  uint64_t addr;
  size_t len;
  uint64_t id;
  std::unique_ptr<uint8_t[]> buf;
  size_t step_size;
  bool completed = false;

  AXIOperation(uint64_t addr, size_t len, uint64_t axi_id, size_t step_size)
      : addr(addr),
        len(len),
        id(axi_id),
        buf(std::make_unique<uint8_t[]>(len)),
        step_size(step_size) {
  }
};

/* Acts as the read part of an AXI Subordinate / Slave component */
template <size_t BytesAddr, size_t BytesId, size_t BytesData,
          size_t MaxInFlight = 64>
class AXISubordinateRead {
 public:
  static_assert(BytesAddr <= 8);
  static_assert(BytesId <= 8);

 private:
  /* address channel */
  const uint8_t *const ar_addr_;
  const uint8_t *const ar_id_;

  uint8_t &ar_ready_;
  const uint8_t &ar_valid_;
  const uint8_t &ar_len_;
  const uint8_t &ar_size_;
  const uint8_t &ar_burst_;

  /* data channel */
  uint8_t *const r_data_;
  uint8_t *const r_id_;

  const uint8_t &r_ready_;
  uint8_t &r_valid_;
  uint8_t &r_last_;

  /* Temp values for outputs. We can't update the outputs directly in `step()`
  since that violates the semantics of non-blocking assignments. */
  uint8_t ar_ready_tmp_ = 0;
  uint8_t r_valid_tmp_ = 0;
  uint8_t r_last_tmp_ = 0;
  uint8_t r_data_tmp_[BytesData] = {0};
  uint32_t r_id_tmp_;

  uint64_t main_time_ = 0;
  std::deque<AXIOperation> pending_{};
  /* map from SimBricks ID to AXI op stored in pending_ */
  std::unordered_map<uint64_t, std::reference_wrapper<AXIOperation>>
      id_op_map_{};
  AXIOperation *cur_op_ = nullptr;
  size_t cur_off_ = 0;
  uint32_t rolling_id_ = 0;

 public:
  AXISubordinateRead(const uint8_t *const ar_addr, const uint8_t *const ar_id,
                     uint8_t &ar_ready, const uint8_t &ar_valid,
                     const uint8_t &ar_len, const uint8_t &ar_size,
                     const uint8_t &ar_burst, uint8_t *const r_data,
                     uint8_t *const r_id, const uint8_t &r_ready,
                     uint8_t &r_valid, uint8_t &r_last)
      : ar_addr_(ar_addr),
        ar_id_(ar_id),
        ar_ready_(ar_ready),
        ar_valid_(ar_valid),
        ar_len_(ar_len),
        ar_size_(ar_size),
        ar_burst_(ar_burst),
        r_data_(r_data),
        r_id_(r_id),
        r_ready_(r_ready),
        r_valid_(r_valid),
        r_last_(r_last) {
  }

  void read_done(uint64_t axi_id, const uint8_t *data);
  /*
    Performs a step on the Subordinate interface, i.e. update the output signals
    based on the inputs.

    This function doesn't apply the outputs yet. This is necessary to properly
    model the semantics of non-blocking writes, i.e. the changes only become
    visible to the Manager in the next clock cycle. To apply the output changes,
    call `step_apply()`. In Verilator, call this function before `eval()`.
  */
  void step(uint64_t cur_ts);
  /*
    Applies the output changes. In Verilator, call this function after `eval()`.
  */
  void step_apply();

 protected:
  virtual void do_read(const AXIOperation &axi_op) = 0;

 private:
  void send_next_data_segment();
};

/* Acts as the write part of an AXI Subordinate / Slave component */
template <size_t BytesAddr, size_t BytesId, size_t BytesData,
          size_t MaxInFlight = 64>
class AXISubordinateWrite {
 public:
  static_assert(BytesAddr <= 8);
  static_assert(BytesId <= 4);

 private:
  /* address channel */
  const uint8_t *const aw_addr_;
  const uint8_t *const aw_id_;

  uint8_t &aw_ready_;
  const uint8_t &aw_valid_;
  const uint8_t &aw_len_;
  const uint8_t &aw_size_;
  const uint8_t &aw_burst_;

  /* data channel */
  const uint8_t *const w_data_;

  uint8_t &w_ready_;
  const uint8_t &w_valid_;
  const uint8_t &w_strb_;
  const uint8_t &w_last_;

  /* response channel */
  uint8_t *const b_id_;

  const uint8_t &b_ready_;
  uint8_t &b_valid_;
  uint8_t &b_resp_;

  /* Temp values for outputs. We can't update the outputs directly in `step()`
  since that violates the semantics of non-blocking assignments. */
  uint8_t aw_ready_tmp_ = 0;
  uint8_t w_ready_tmp_ = 0;
  uint8_t b_valid_tmp_ = 0;
  uint64_t b_id_tmp_ = 0;

  uint64_t main_time_ = 0;
  uint64_t cur_off_ = 0;
  uint64_t num_pending_ = 0;
  std::optional<AXIOperation> cur_op_ = std::nullopt;

 public:
  AXISubordinateWrite(const uint8_t *aw_addr, const uint8_t *aw_id,
                      uint8_t &aw_ready, const uint8_t &aw_valid,
                      const uint8_t &aw_len, const uint8_t &aw_size,
                      const uint8_t &aw_burst, const uint8_t *w_data,
                      uint8_t &w_ready, const uint8_t &w_valid,
                      const uint8_t &w_strb, const uint8_t &w_last,
                      uint8_t *b_id, const uint8_t &b_ready, uint8_t &b_valid,
                      uint8_t &b_resp)
      : aw_addr_(aw_addr),
        aw_id_(aw_id),
        aw_ready_(aw_ready),
        aw_valid_(aw_valid),
        aw_len_(aw_len),
        aw_size_(aw_size),
        aw_burst_(aw_burst),
        w_data_(w_data),
        w_ready_(w_ready),
        w_valid_(w_valid),
        w_strb_(w_strb),
        w_last_(w_last),
        b_id_(b_id),
        b_ready_(b_ready),
        b_valid_(b_valid),
        b_resp_(b_resp) {
  }

  void write_done(uint64_t axi_id);
  /*
    Performs a step on the Subordinate interface, i.e. update the output signals
    based on the inputs.

    This function doesn't apply the outputs yet. This is necessary to properly
    model the semantics of non-blocking writes, i.e. the changes only become
    visible to the Manager in the next clock cycle. To apply the output changes,
    call `step_apply()`. In Verilator, call this function before `eval()`.
  */
  void step(uint64_t cur_ts);
  /*
    Applies the output changes. In Verilator, call this function after `eval()`.
  */
  void step_apply();

 protected:
  virtual void do_write(const AXIOperation &axi_op) = 0;
};

/******************************************************************************/
/* Start of implementation. We need to put this into the header as code for
template classes is only emitted at instantiation. */
/******************************************************************************/

inline uint64_t pow2(uint64_t exponent) {
  return 1 << exponent;
}

/******************************************************************************/
/* AXISubordinateRead */
/******************************************************************************/

template <size_t BytesAddr, size_t BytesId, size_t BytesData,
          size_t MaxInFlight>
void AXISubordinateRead<BytesAddr, BytesId, BytesData, MaxInFlight>::step(
    uint64_t cur_ts) {
  main_time_ = cur_ts;

  /* data stream complete */
  if (r_last_ && r_valid_ && r_ready_) {
#if AXI_R_DEBUG
    std::cout << main_time_ << " AXI R: completed id=0x" << std::hex
              << cur_op_->id << std::dec << "\n";
#endif
    id_op_map_.erase(cur_op_->id);
    cur_op_ = nullptr;
    pending_.pop_front();
    cur_off_ = 0;
    r_valid_tmp_ = 0;
    r_last_tmp_ = 0;
    std::memset(r_data_tmp_, 0, BytesData);
    r_id_tmp_ = 0;
  } else if (r_ready_ && r_valid_) {
    /* data handshake complete, issue the next data segment */
#if AXI_R_DEBUG
    std::cout << main_time_ << " AXI R: data handshake id=0x" << std::hex
              << cur_op_->id << std::dec << " off=" << cur_off_ << "\n";
#endif
    send_next_data_segment();
  }

  /* new read request */
  if (ar_ready_ && ar_valid_) {
    uint32_t axi_id = 0;
    std::memcpy(&axi_id, ar_id_, BytesId);
    uint64_t addr = 0;
    std::memcpy(&addr, ar_addr_, BytesAddr);

    uint64_t step_size = pow2(ar_size_);
    assert(ar_burst_ == 1 && "we currently only support INCR bursts");
    uint64_t simbricks_id = static_cast<uint64_t>(axi_id) << 32 | rolling_id_++;
    AXIOperation &axi_op = pending_.emplace_back(
        addr, step_size * (ar_len_ + 1), simbricks_id, step_size);
    auto res = id_op_map_.emplace(simbricks_id, axi_op);
    assert(
        res.second &&
        "AXISubordinateRead::step() id_op_map_.emplace() must be successful");
#if AXI_R_DEBUG
    std::cout << main_time_ << " AXI R: new op addr=" << axi_op.addr
              << " len=" << axi_op.len << " id=0x" << std::hex << axi_op.id
              << std::dec << "\n";
#endif
    do_read(axi_op);
  }

  /* only accept up to MaxInFlight requests */
  ar_ready_tmp_ = pending_.size() < MaxInFlight ? 1 : 0;

  /* initiate stream for fetched data */
  if (cur_op_ == nullptr && !pending_.empty()) {
    AXIOperation &axi_op = pending_.front();
    if (axi_op.completed) {
#if AXI_R_DEBUG
      std::cout << main_time_ << " AXI R: starting response id=0x" << std::hex
                << axi_op.id << std::dec << "\n";
#endif
      cur_op_ = &axi_op;
      r_valid_tmp_ = 1;
      r_id_tmp_ = cur_op_->id >> 32;
      send_next_data_segment();
    }
  }
}

template <size_t BytesAddr, size_t BytesId, size_t BytesData,
          size_t MaxInFlight>
void AXISubordinateRead<BytesAddr, BytesId, BytesData,
                        MaxInFlight>::step_apply() {
  ar_ready_ = ar_ready_tmp_;
  r_valid_ = r_valid_tmp_;
  r_last_ = r_last_tmp_;
  std::memcpy(r_data_, r_data_tmp_, BytesData);
  std::memcpy(r_id_, &r_id_tmp_, BytesId);
}

template <size_t BytesAddr, size_t BytesId, size_t BytesData,
          size_t MaxInFlight>
void AXISubordinateRead<BytesAddr, BytesId, BytesData, MaxInFlight>::read_done(
    uint64_t simbricks_id, const uint8_t *data) {
#if AXI_R_DEBUG
  std::cout << main_time_ << " AXI R: read_done id=0x" << std::hex
            << simbricks_id << std::dec << "\n";
#endif
  AXIOperation &axi_op = id_op_map_.at(simbricks_id);
  std::memcpy(axi_op.buf.get(), data, axi_op.len);
  axi_op.completed = true;
}

template <size_t BytesAddr, size_t BytesId, size_t BytesData,
          size_t MaxInFlight>
void AXISubordinateRead<BytesAddr, BytesId, BytesData,
                        MaxInFlight>::send_next_data_segment() {
  size_t align = (cur_op_->addr + cur_off_) % BytesData;
  size_t num_bytes = std::min(BytesData - align, cur_op_->step_size);
  std::memset(r_data_tmp_, 0, BytesData);
  std::memcpy(r_data_tmp_ + align, cur_op_->buf.get() + cur_off_, num_bytes);

  cur_off_ += num_bytes;
  r_last_tmp_ = cur_off_ == cur_op_->len;
}

/******************************************************************************/
/* AXISubordinateWrite */
/******************************************************************************/

template <size_t BytesAddr, size_t BytesId, size_t BytesData,
          size_t MaxInFlight>
void AXISubordinateWrite<BytesAddr, BytesId, BytesData, MaxInFlight>::step(
    uint64_t cur_ts) {
  main_time_ = cur_ts;
  b_resp_ = 0;

  /* write response handshake complete */
  if (b_valid_ && b_ready_) {
#if AXI_W_DEBUG
    std::cout << main_time_
              << " AXI W: response handshake complete id=" << b_id_tmp_ << "\n";
#endif
    b_valid_tmp_ = 0;
    b_id_tmp_ = 0;
    cur_op_ = std::nullopt;
  }

  /* handshake on address port, Manager is issuing new write request */
  if (aw_valid_ && aw_ready_) {
    uint32_t axi_id = 0;
    std::memcpy(&axi_id, aw_id_, BytesId);

    uint64_t addr = 0;
    std::memcpy(&addr, aw_addr_, BytesAddr);

    uint64_t step_size = pow2(aw_size_);
    assert(aw_burst_ == 1 && "we currently only support INCR bursts");
    size_t len = step_size * (aw_len_ + 1);
#if AXI_W_DEBUG
    std::cout << main_time_ << " AXI W: new request id=" << axi_id
              << " addr=" << addr << " len=" << len
              << " step_size=" << step_size << "\n";
#endif
    cur_op_.emplace(addr, len, axi_id, step_size);
    w_ready_tmp_ = 1;
  }

  /* handshake on data port, read next segment*/
  if (w_valid_ && w_ready_) {
    size_t align = (cur_op_->addr + cur_off_) % BytesData;
#if AXI_W_DEBUG
    std::cout << "AXI W next segment: id=" << cur_op_->id
              << " cur_off=" << cur_off_ << " step_size=" << cur_op_->step_size
              << " align=" << align << "\n";
#endif
    size_t num_bytes = std::min(BytesData - align, cur_op_->step_size);
    std::memcpy(cur_op_->buf.get() + cur_off_, w_data_ + align, num_bytes);
    cur_off_ += num_bytes;
    assert(cur_off_ <= cur_op_->len && "AXI W cur_off_ > cur_op_->len");

    /* last segment of data, send write request */
    if (w_last_) {
#if AXI_W_DEBUG
      std::cout << "AXI W Issuing request for id=" << cur_op_->id
                << " addr=" << cur_op_->addr << " len=" << cur_op_->len << "\n";
#endif
      do_write(*cur_op_);
      num_pending_++;
      cur_off_ = 0;
      w_ready_tmp_ = 0;
      b_id_tmp_ = cur_op_->id;
      b_valid_tmp_ = 1;
    }
  }

  aw_ready_tmp_ = !cur_op_ && num_pending_ < MaxInFlight;
}

template <size_t BytesAddr, size_t BytesId, size_t BytesData,
          size_t MaxInFlight>
void AXISubordinateWrite<BytesAddr, BytesId, BytesData,
                         MaxInFlight>::step_apply() {
  b_valid_ = b_valid_tmp_;
  std::memcpy(b_id_, &b_id_tmp_, BytesId);
  aw_ready_ = aw_ready_tmp_;
  w_ready_ = w_ready_tmp_;
}

template <size_t BytesAddr, size_t BytesId, size_t BytesData,
          size_t MaxInFlight>
void AXISubordinateWrite<BytesAddr, BytesId, BytesData,
                         MaxInFlight>::write_done(uint64_t axi_id) {
#if AXI_W_DEBUG
  std::cout << main_time_ << " AXI W completed write for id=" << axi_id << "\n";
#endif
  num_pending_--;
}
}  // namespace simbricks
#endif  // SIMBRICKS_AXI_AXI_SUBORDINATE_HH_
