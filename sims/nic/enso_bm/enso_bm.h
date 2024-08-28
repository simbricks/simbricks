/*
 * Copyright (c) 2021-2024, Max Planck Institute for Software Systems,
 * National University of Singapore, and Carnegie Mellon University
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted (subject to the limitations in the disclaimer
 * below) provided that the following conditions are met:
 *
 *      * Redistributions of source code must retain the above copyright notice,
 *      this list of conditions and the following disclaimer.
 *
 *      * Redistributions in binary form must reproduce the above copyright
 *      notice, this list of conditions and the following disclaimer in the
 *      documentation and/or other materials provided with the distribution.
 *
 *      * Neither the name of the copyright holder nor the names of its
 *      contributors may be used to endorse or promote products derived from
 *      this software without specific prior written permission.
 *
 * NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY
 * THIS LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
 * CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
 * NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
 * PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
 * OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
 * OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
 * ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#pragma once

#include <cstdint>
#include <unordered_map>
#include <utility>

extern "C" {
#include <simbricks/pcie/proto.h>
}
#include <simbricks/nicbm/nicbm.h>

#include "sims/nic/enso_bm/enso_config.h"
#include "sims/nic/enso_bm/enso_helpers.h"

// #define DEBUG_DEV

namespace enso_bm {

class enso_bm;

constexpr uint32_t VENDOR_ID = 0x1172;
constexpr uint32_t DEVICE_ID = 0x0;
constexpr uint32_t STANDARD_BAR = 0;
constexpr uint32_t QUEUES_BAR = 2;
constexpr uint32_t MSIX_BAR = 3;

constexpr uint32_t MAX_NB_APPS = 1024;
constexpr uint32_t MAX_NB_QUEUES = 8192;

constexpr uint32_t MTU = 1500;

// Both buffer sizes are in number of flits (64B).
constexpr uint32_t ENSO_PIPE_SIZE = 32768;
constexpr uint32_t NOTIFICATION_BUF_SIZE = 16384;

constexpr uint32_t MEMORY_SPACE_PER_QUEUE = 1 << 12;

class dma_base : public nicbm::DMAOp {
 public:
  explicit dma_base(enso_bm *context);
  virtual ~dma_base() = default;

  /** enso_bm will call this when dma is done */
  virtual void done() = 0;

  void Issue();

 protected:
  enso_bm* context_;
  dma_base *next_dma_ = nullptr;
};

class dma_write : public dma_base {
 public:
  dma_write(enso_bm *context, uint64_t dest_addr, size_t len, const uint8_t *data, logger &log);
  virtual ~dma_write();
  virtual void done();

 private:
  logger &log_;
};

class dma_read : public dma_base {
 public:
  dma_read(enso_bm *context, uint64_t source_addr, size_t len, uint8_t *buffer, logger &log);
  virtual ~dma_read();
  virtual void done();

 private:
  logger &log_;
};

class rx_pipeline {
 public:
  bool enable_rr = false;

  rx_pipeline(enso_bm *context);
  virtual ~rx_pipeline();
  void enqueue_packet(const uint8_t *data, size_t len);
  void add_flow_table_entry(uint16_t dst_port, uint16_t src_port,
                            uint32_t dst_ip, uint32_t src_ip,
                            uint32_t enso_pipe_id);
  void set_fallback_queues(uint32_t fallback_queues,
                           uint32_t fallback_queue_mask);

  void reset();

 private:
  enso_bm *context_;
  std::unordered_map<four_tuple, uint32_t> flow_table_;
  uint32_t fallback_queues_ = 0;
  uint32_t fallback_queue_mask_ = 0;
  uint32_t next_queue_ = 0;  // Used for round-robin.

  void flow_director(const uint8_t *data, size_t len);
};

class tx_pipeline {
 public:
  tx_pipeline(enso_bm *context);
  virtual ~tx_pipeline();
  void enqueue_data(const uint8_t *data, size_t len);

  void reset();

 private:
  enso_bm *context_;
  uint8_t incomplete_pkt_buf_[MTU + 18];
  uint32_t total_pkt_len_ = 0;
  uint32_t incomplete_pkt_len_ = 0;
};

class enso_bm : public nicbm::Runner::Device {
 public:
  logger log;

  enso_bm();
  ~enso_bm();

  void SetupIntro(struct SimbricksProtoPcieDevIntro &di) override;
  void RegRead(uint8_t bar, uint64_t addr, void *dest, size_t len) override;
  virtual uint32_t RegRead32(uint8_t bar, uint64_t addr);
  void RegWrite(uint8_t bar, uint64_t addr, const void *src,
                size_t len) override;
  virtual void RegWrite32(uint8_t bar, uint64_t addr, uint32_t val);
  void DmaComplete(nicbm::DMAOp &op) override;
  void EthRx(uint8_t port, const void *data, size_t len) override;
  void Timed(nicbm::TimedEvent &ev) override;

  void DmaData(const uint8_t *data, size_t len, uint32_t pipe_id);
  void SendEthPacket(const uint8_t *data, size_t len);

 private:
  struct ring_buf {
    uint8_t *buf = nullptr;
    uint32_t tail = 0;
    uint32_t head = 0;
  };

  struct queue_regs {
    uint32_t rx_tail;
    uint32_t rx_head;
    uint32_t rx_mem_low;
    uint32_t rx_mem_high;
    uint32_t tx_tail;
    uint32_t tx_head;
    uint32_t tx_mem_low;
    uint32_t tx_mem_high;
    uint32_t padding[8];
  };

  struct __attribute__((__packed__)) rx_notification {
    uint64_t signal;
    uint64_t queue_id;
    uint64_t tail;
    uint64_t pad[5];
  };

  struct __attribute__((__packed__)) tx_notification {
    uint64_t signal;
    uint64_t phys_addr;
    uint64_t length;  // In bytes (up to 1MB).
    uint64_t pad[5];
  };

  class dma_read_tx_notif : public dma_base {
   public:
    dma_read_tx_notif(enso_bm *context, uint32_t queue_id, uint32_t old_tail,
                      logger &log);
    virtual ~dma_read_tx_notif();
    virtual void done();

   private:
    uint32_t queue_id_;
    uint32_t old_tail_;
    logger &log_;
  };

  class dma_read_data : public dma_base {
   public:
    dma_read_data(enso_bm *context, uint64_t source_addr, size_t len,
                  dma_write *completion_dma, logger &log);
    virtual ~dma_read_data();
    virtual void done();

   private:
    dma_write *completion_dma_;
    logger &log_;
  };

  struct stats {
    uint64_t rx_pkts = 0;
    uint64_t tx_pkts = 0;
    uint64_t pkt_drops = 0;
    uint64_t notif_drops = 0;
  } stats_;

  /** Application RX buffers indexed by pipe ID */
  std::array<struct ring_buf, MAX_NB_QUEUES> rx_bufs_ = {0};

  std::array<struct ring_buf, MAX_NB_QUEUES> rx_notif_bufs_ = {0};
  std::array<struct ring_buf, MAX_NB_QUEUES> tx_notif_bufs_ = {0};

  rx_pipeline rx_pipeline_;
  tx_pipeline tx_pipeline_;

  /** 32-bit read from the memory bar (should be the default) */
  virtual uint32_t reg_mem_read32(uint64_t addr);
  /** 32-bit write to the memory bar (should be the default) */
  virtual void reg_mem_write32(uint64_t addr, uint32_t val);

  void send_rx_notif(uint32_t queue);

  void process_tx_notif(tx_notification *notification,
                        uint64_t completion_addr);

  void process_config(config::config *config);

  void process_flow_table_config(config::flow_table *flow_table);

  void process_timestamp_config(config::timestamp *timestamp);

  void process_rate_limit_config(config::rate_limit *queue);

  void process_fallback_queues_config(config::fallback_queue *fallback_queues);

  void reset();
};

}  // namespace enso_bm
