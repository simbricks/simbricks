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

#include "sims/nic/enso_bm/enso_bm.h"

#include <stdlib.h>
#include <string.h>

#include <cassert>
#include <iostream>

#include "lib/simbricks/nicbm/multinic.h"
#include "sims/nic/enso_bm/enso_config.h"
#include "sims/nic/enso_bm/enso_helpers.h"
#include "sims/nic/enso_bm/headers.h"

namespace enso_bm {

dma_base::dma_base(enso_bm *context) : context_(context) {
}

void dma_base::Issue() {
  context_->runner_->IssueDma(*this);
  if (next_dma_) {
    next_dma_->Issue();
  }
}

dma_write::dma_write(enso_bm *context, uint64_t dest_addr, size_t len,
                     const uint8_t *data, logger &log)
    : dma_base(context), log_(log) {
  write_ = true;
  dma_addr_ = dest_addr;
  len_ = len;
  data_ = new uint8_t[len];
  memcpy(data_, data, len);
}

dma_write::~dma_write() {
  delete[] ((uint8_t *)data_);
}

void dma_write::done() {
  delete this;
}

dma_read::dma_read(enso_bm *context, uint64_t source_addr, size_t len,
                   uint8_t *buffer, logger &log)
    : dma_base(context), log_(log) {
  write_ = false;
  dma_addr_ = source_addr;
  len_ = len;
  data_ = buffer;
}

dma_read::~dma_read() {
}

void dma_read::done() {
  delete this;
}

rx_pipeline::rx_pipeline(enso_bm *context) {
  context_ = context;
}

rx_pipeline::~rx_pipeline() {
}

void rx_pipeline::enqueue_packet(const uint8_t *data, size_t len) {
  flow_director(data, len);
}

void rx_pipeline::add_flow_table_entry(uint16_t dst_port, uint16_t src_port,
                                       uint32_t dst_ip, uint32_t src_ip,
                                       uint32_t enso_pipe_id) {
  four_tuple tuple = {dst_port, src_port, dst_ip, src_ip};
#ifdef DEBUG_DEV
  context_->log << "RX: Adding flow table entry: dst_port=" << dst_port
                << " src_port=" << src_port << " dst_ip=" << dst_ip
                << " src_ip=" << src_ip << " enso_pipe_id=" << enso_pipe_id
                << logger::endl;
#endif
  flow_table_.insert_or_assign(tuple, enso_pipe_id);
}

void rx_pipeline::set_fallback_queues(uint32_t fallback_queues,
                                      uint32_t fallback_queue_mask) {
  fallback_queues_ = fallback_queues;
  fallback_queue_mask_ = fallback_queue_mask;
}

void rx_pipeline::reset() {
  flow_table_.clear();
  fallback_queues_ = 0;
  fallback_queue_mask_ = 0;
  next_queue_ = 0;
}

void rx_pipeline::flow_director(const uint8_t *data, size_t len) {
  // Extract four-tuple from packet.
  const headers::eth_hdr *eth =
      reinterpret_cast<const headers::eth_hdr *>(data);
  const headers::ip_hdr *ip =
      reinterpret_cast<const headers::ip_hdr *>(eth + 1);

  struct four_tuple tuple;

  if (ip->proto == IP_PROTO_TCP) {
    const headers::tcp_hdr *tcp =
        reinterpret_cast<const headers::tcp_hdr *>(ip + 1);
    tuple = {be_to_le_16(tcp->dest), be_to_le_16(tcp->src),
             be_to_le_32(ip->dest), be_to_le_32(ip->src)};
  } else if (ip->proto == IP_PROTO_UDP) {
    const headers::udp_hdr *udp =
        reinterpret_cast<const headers::udp_hdr *>(ip + 1);
    tuple = {be_to_le_16(udp->dest), 0, be_to_le_32(ip->dest), 0};
  } else {
    tuple = {0, 0, be_to_le_32(ip->dest), 0};
  }

#ifdef DEBUG_DEV
  context_->log << "RX: Flow director: dst_port=" << tuple.dst_port
                << " src_port=" << tuple.src_port << " dst_ip=" << tuple.dst_ip
                << " src_ip=" << tuple.src_ip << logger::endl;
#endif
  uint32_t pipe_id = 0;

  // Check if packet matches flow table.
  auto it = flow_table_.find(tuple);
  if (it != flow_table_.end()) {
    // Send packet to matched enso pipe.
    pipe_id = it->second;

  } else {
    if (fallback_queues_ == 0) {
      // Drop packet.
#ifdef DEBUG_DEV
      context_->log << "RX: Packet dropped" << logger::endl;
#endif
      return;
    }

    // Send packet to fallback queue.
    if (enable_rr) {
      // Round robin.
      pipe_id = next_queue_;
      next_queue_ = (next_queue_ + 1) & fallback_queue_mask_;
    } else {
      // Hash.
      pipe_id = std::hash<struct four_tuple>{}(tuple)&fallback_queue_mask_;
    }
  }
#ifdef DEBUG_DEV
  context_->log << "RX: Sending packet to enso pipe " << pipe_id
                << logger::endl;
#endif
  context_->DmaData(data, len, pipe_id);
}

enso_bm::dma_read_tx_notif::dma_read_tx_notif(enso_bm *context,
                                              uint32_t queue_id,
                                              uint32_t old_tail, logger &log)
    : dma_base(context), log_(log) {
  context_ = context;
  queue_id_ = queue_id;

  tx_notification *notif_buf = reinterpret_cast<tx_notification *>(
      context_->tx_notif_bufs_[queue_id].buf);

  write_ = false;
  dma_addr_ = reinterpret_cast<uint64_t>(&notif_buf[old_tail]);

  // If the tail has wrapped around, we need to read the notifications in two
  // steps.
  uint32_t tail = context->tx_notif_bufs_[queue_id].tail;
  if (old_tail > tail && tail != 0) {
    next_dma_ = new dma_read_tx_notif(context_, queue_id_, 0, log);
    tail = 0;
  }

  len_ = ((tail - old_tail) % NOTIFICATION_BUF_SIZE) * sizeof(tx_notification);
  data_ = new uint8_t[len_];
}

enso_bm::dma_read_tx_notif::~dma_read_tx_notif() {
  delete[] ((uint8_t *)data_);
}

void enso_bm::dma_read_tx_notif::done() {
  tx_notification *notifications = reinterpret_cast<tx_notification *>(data_);
  size_t nb_notifications = len_ / sizeof(tx_notification);

  for (size_t i = 0; i < nb_notifications; i++) {
    uint64_t completion_addr = dma_addr_ + i * sizeof(tx_notification);
    context_->process_tx_notif(&notifications[i], completion_addr);
  }
  delete this;
}

enso_bm::dma_read_data::dma_read_data(enso_bm *context, uint64_t source_addr,
                                      size_t len, dma_write *completion_dma,
                                      logger &log)
    : dma_base(context), log_(log) {
  context_ = context;
  write_ = false;
  completion_dma_ = completion_dma;
  dma_addr_ = source_addr;

  if (len > nicbm::kMaxDmaLen) {
    next_dma_ = new dma_read_data(context, source_addr + nicbm::kMaxDmaLen,
                                  len - nicbm::kMaxDmaLen, completion_dma, log);
    len = nicbm::kMaxDmaLen;
  }
  len_ = len;

  data_ = new uint8_t[len];
}

enso_bm::dma_read_data::~dma_read_data() {
  delete[] ((uint8_t *)data_);
}

void enso_bm::dma_read_data::done() {
  // Last DMA read operation, issue completion DMA.
  if (next_dma_ == nullptr) {
    completion_dma_->Issue();
  }

  context_->tx_pipeline_.enqueue_data(reinterpret_cast<uint8_t *>(data_), len_);

  delete this;
}

tx_pipeline::tx_pipeline(enso_bm *context) : context_(context) {
}

tx_pipeline::~tx_pipeline() {
}

void tx_pipeline::enqueue_data(const uint8_t *data, size_t len) {
#ifdef DEBUG_DEV
  context_->log << "TX pipeline: enqueue data len=0x" << len << logger::endl;
#endif

  const uint8_t *cur_data = data;
  int32_t missing_len = len;
  while (missing_len > 0) {
    if (incomplete_pkt_len_ != 0) {
      // Append incomplete packet to current data.
      int32_t missing_pkt_len = total_pkt_len_ - incomplete_pkt_len_;

      assert(missing_pkt_len > missing_len);

      memcpy(incomplete_pkt_buf_ + incomplete_pkt_len_, cur_data,
             missing_pkt_len);

      context_->SendEthPacket(incomplete_pkt_buf_, total_pkt_len_);

      missing_len -= missing_pkt_len;
      cur_data += missing_pkt_len;

      total_pkt_len_ = 0;
      incomplete_pkt_len_ = 0;

      continue;
    }

    // Parse packets and check if it is incomplete.
    const headers::eth_hdr *eth =
        reinterpret_cast<const headers::eth_hdr *>(cur_data);
    const headers::ip_hdr *ip =
        reinterpret_cast<const headers::ip_hdr *>(eth + 1);
    size_t packet_length = le_to_be_16(ip->len) + sizeof(headers::eth_hdr);
    size_t aligned_length = (packet_length + 63) & ~63;

    if (static_cast<int32_t>(packet_length) > missing_len) {
      // Incomplete packet.
      memcpy(incomplete_pkt_buf_, cur_data, missing_len);
      total_pkt_len_ = packet_length;
      incomplete_pkt_len_ = missing_len;
      break;
    }

    // Send packet to Ethernet.
    context_->SendEthPacket(cur_data, packet_length);

    cur_data += aligned_length;
    missing_len -= aligned_length;
  }
}

void tx_pipeline::reset() {
  total_pkt_len_ = 0;
  incomplete_pkt_len_ = 0;
}

enso_bm::enso_bm()
    : log("enso", dynamic_cast<nicbm::Runner::Device &>(*this)),
      rx_pipeline_(this),
      tx_pipeline_(this) {
  reset();
}

enso_bm::~enso_bm() {
}

void enso_bm::SetupIntro(struct SimbricksProtoPcieDevIntro &di) {
  di.bars[STANDARD_BAR].len = 1 << 16;
  di.bars[STANDARD_BAR].flags = SIMBRICKS_PROTO_PCIE_BAR_64 |
                                SIMBRICKS_PROTO_PCIE_BAR_PF |
                                SIMBRICKS_PROTO_PCIE_BAR_DUMMY;
  di.bars[QUEUES_BAR].len = 1 << 30;
  di.bars[QUEUES_BAR].flags =
      SIMBRICKS_PROTO_PCIE_BAR_64 | SIMBRICKS_PROTO_PCIE_BAR_PF;

  di.pci_vendor_id = VENDOR_ID;
  di.pci_device_id = DEVICE_ID;
  di.pci_class = 0x02;
  di.pci_subclass = 0x00;
  di.pci_revision = 0x00;
  di.pci_msi_nvecs = 32;
}

void enso_bm::DmaComplete(nicbm::DMAOp &op) {
  dma_base &dma = dynamic_cast<dma_base &>(op);
  dma.done();
}

void enso_bm::EthRx(uint8_t port, const void *data, size_t len) {
#ifdef DEBUG_DEV
  log << "received packet len=" << len << logger::endl;
#endif
  stats_.rx_pkts++;
  rx_pipeline_.enqueue_packet(reinterpret_cast<const uint8_t *>(data), len);
}

void enso_bm::RegRead(uint8_t bar, uint64_t addr, void *dest, size_t len) {
  uint32_t *dest_p = reinterpret_cast<uint32_t *>(dest);

  if (len == 4) {
    dest_p[0] = RegRead32(bar, addr);
  } else if (len == 8) {
    dest_p[0] = RegRead32(bar, addr);
    dest_p[1] = RegRead32(bar, addr + 4);
  } else {
    log << "currently we only support 4/8B reads (got " << len << ")"
        << logger::endl;
    abort();
  }
}

uint32_t enso_bm::RegRead32(uint8_t bar, uint64_t addr) {
  if (bar != QUEUES_BAR) {
    log << "invalid BAR " << (int)bar << logger::endl;
    abort();
  }
  return reg_mem_read32(addr);
}

void enso_bm::RegWrite(uint8_t bar, uint64_t addr, const void *src,
                       size_t len) {
  const uint32_t *src_p = reinterpret_cast<const uint32_t *>(src);

  if (len == 4) {
    RegWrite32(bar, addr, src_p[0]);
  } else if (len == 8) {
    RegWrite32(bar, addr, src_p[0]);
    RegWrite32(bar, addr + 4, src_p[1]);
  } else {
    log << "currently we only support 4/8B writes (got " << len << ")"
        << logger::endl;
    abort();
  }
}

void enso_bm::RegWrite32(uint8_t bar, uint64_t addr, uint32_t val) {
  if (bar != QUEUES_BAR) {
    log << "invalid BAR " << (int)bar << logger::endl;
    abort();
  }
  reg_mem_write32(addr, val);
}

uint32_t enso_bm::reg_mem_read32(uint64_t addr) {
  uint32_t val = 0;

  uint32_t queue_id = addr / MEMORY_SPACE_PER_QUEUE;
  uint32_t offset = addr % MEMORY_SPACE_PER_QUEUE;

  // Reads to RX pipe.
  if ((queue_id < MAX_NB_QUEUES)) {
    switch (offset) {
      case offsetof(struct queue_regs, rx_tail):
        val = rx_bufs_[queue_id].tail;
        break;

      case offsetof(struct queue_regs, rx_head):
        val = rx_bufs_[queue_id].head;
        break;

      case offsetof(struct queue_regs, rx_mem_low):
        val = reinterpret_cast<uint64_t>(rx_bufs_[queue_id].buf) & 0xffffffff;
        break;

      case offsetof(struct queue_regs, rx_mem_high):
        val = reinterpret_cast<uint64_t>(rx_bufs_[queue_id].buf) >> 32;
        break;

      default:
        log << "unhandled mem read addr=" << addr << logger::endl;
        break;
    }
  } else {
    queue_id -= MAX_NB_QUEUES;

    // Reads to notification buffers.
    if (queue_id < MAX_NB_APPS) {
      switch (offset) {
        case offsetof(struct queue_regs, rx_tail):
          val = rx_notif_bufs_[queue_id].tail;
          break;

        case offsetof(struct queue_regs, rx_head):
          val = rx_notif_bufs_[queue_id].head;
          break;

        case offsetof(struct queue_regs, rx_mem_low):
          val = reinterpret_cast<uint64_t>(rx_notif_bufs_[queue_id].buf);
          break;

        case offsetof(struct queue_regs, rx_mem_high):
          val = reinterpret_cast<uint64_t>(rx_notif_bufs_[queue_id].buf) >> 32;
          break;

        case offsetof(struct queue_regs, tx_tail):
          val = tx_notif_bufs_[queue_id].tail;
          break;

        case offsetof(struct queue_regs, tx_head):
          val = tx_notif_bufs_[queue_id].head;
          break;

        case offsetof(struct queue_regs, tx_mem_low):
          val = reinterpret_cast<uint64_t>(tx_notif_bufs_[queue_id].buf);
          break;

        case offsetof(struct queue_regs, tx_mem_high):
          val = reinterpret_cast<uint64_t>(tx_notif_bufs_[queue_id].buf) >> 32;
          break;

        default:
          log << "unhandled mem read addr=" << addr << logger::endl;
          break;
      }
    } else {
      log << "unhandled mem read addr=" << addr << logger::endl;
    }
  }

  return val;
}

void enso_bm::reg_mem_write32(uint64_t addr, uint32_t val) {
  uint32_t queue_id = addr / MEMORY_SPACE_PER_QUEUE;
  uint32_t offset = addr % MEMORY_SPACE_PER_QUEUE;

  uint64_t value = val;

  // Updates to RX pipe.
  if (queue_id < MAX_NB_QUEUES) {
    switch (offset) {
      case offsetof(struct queue_regs, rx_tail):
        rx_bufs_[queue_id].tail = value;
        break;

      case offsetof(struct queue_regs, rx_head):
        rx_bufs_[queue_id].head = value;

        // Reactive notification: Send notification if there is new data.
        if (rx_bufs_[queue_id].head != rx_bufs_[queue_id].tail) {
          send_rx_notif(queue_id);
        }
        break;

      case offsetof(struct queue_regs, rx_mem_low): {
        uint64_t addr = reinterpret_cast<uint64_t>(rx_bufs_[queue_id].buf);
        rx_bufs_[queue_id].buf =
            reinterpret_cast<uint8_t *>((addr & 0xffffffff00000000) | value);
        break;
      }

      case offsetof(struct queue_regs, rx_mem_high): {
        uint64_t addr = reinterpret_cast<uint64_t>(rx_bufs_[queue_id].buf);
        rx_bufs_[queue_id].buf =
            reinterpret_cast<uint8_t *>((addr & 0xffffffff) | (value << 32));
        break;
      }

      default:
        std::cerr << "Unknown RX pipe register offset: " << offset << std::endl;
        abort();
    }
    return;
  } else {
    queue_id -= MAX_NB_QUEUES;

    // Updates to notification buffers.
    if (queue_id < MAX_NB_APPS) {
      switch (offset) {
        case offsetof(struct queue_regs, rx_tail):
          rx_notif_bufs_[queue_id].tail = value;
          break;

        case offsetof(struct queue_regs, rx_head):
          rx_notif_bufs_[queue_id].head = value;
          break;

        case offsetof(struct queue_regs, rx_mem_low): {
          uint64_t addr =
              reinterpret_cast<uint64_t>(rx_notif_bufs_[queue_id].buf);
          rx_notif_bufs_[queue_id].buf =
              reinterpret_cast<uint8_t *>((addr & 0xffffffff00000000) | value);
          break;
        }

        case offsetof(struct queue_regs, rx_mem_high): {
          uint64_t addr =
              reinterpret_cast<uint64_t>(rx_notif_bufs_[queue_id].buf);
          rx_notif_bufs_[queue_id].buf =
              reinterpret_cast<uint8_t *>((addr & 0xffffffff) | (value << 32));
          break;
        }

        case offsetof(struct queue_regs, tx_tail): {
          uint32_t old_tail = tx_notif_bufs_[queue_id].tail;
          tx_notif_bufs_[queue_id].tail = value;

          if (old_tail != value) {
            // DMA read the new notifications.
            dma_read_tx_notif *dma =
                new dma_read_tx_notif(this, queue_id, old_tail, log);
            dma->Issue();
          }
          break;
        }

        case offsetof(struct queue_regs, tx_head):
          tx_notif_bufs_[queue_id].head = value;
          break;

        case offsetof(struct queue_regs, tx_mem_low): {
          uint64_t addr =
              reinterpret_cast<uint64_t>(tx_notif_bufs_[queue_id].buf);
          tx_notif_bufs_[queue_id].buf =
              reinterpret_cast<uint8_t *>((addr & 0xffffffff00000000) | value);
          break;
        }

        case offsetof(struct queue_regs, tx_mem_high): {
          uint64_t addr =
              reinterpret_cast<uint64_t>(tx_notif_bufs_[queue_id].buf);
          tx_notif_bufs_[queue_id].buf =
              reinterpret_cast<uint8_t *>((addr & 0xffffffff) | (value << 32));
          break;
        }

        default:
          std::cerr << "Unknown notification buffer register offset: " << offset
                    << std::endl;
          exit(1);
      }
    } else {
      log << "unhandled mem write addr=" << addr << " val=" << val
          << logger::endl;
    }
  }
}

void enso_bm::Timed([[maybe_unused]] nicbm::TimedEvent &ev) {
  log << "Unnexpected timed event." << logger::endl;
  abort();
}

void enso_bm::DmaData(const uint8_t *data, size_t len, uint32_t pipe_id) {
  // Align len to 64B.
  size_t aligned_len = (len + 63) & ~63;
  size_t flits = aligned_len / 64;

  struct ring_buf *app_rx_buf = &rx_bufs_[pipe_id];

  uint32_t nb_free_slots =
      (app_rx_buf->head - app_rx_buf->tail - 1) % ENSO_PIPE_SIZE;

#ifdef DEBUG_DEV
  log << "enso: DMA data to pipe " << pipe_id << " len=" << len
      << " aligned_len=" << aligned_len << " flits=" << flits
      << " nb_free_slots=" << nb_free_slots << logger::endl;
#endif

  if (nb_free_slots < flits) {
    // Drop data.
    stats_.pkt_drops++;
#ifdef DEBUG_DEV
    log << "enso: Packet dropped." << logger::endl;
#endif
    return;
  }

  // The least significant bits of the address are used to keep the
  // notification buffer ID.
  uint64_t clean_addr = reinterpret_cast<uint64_t>(app_rx_buf->buf) &
                        ~((uint64_t)MAX_NB_APPS - 1);
  uint8_t *buf = reinterpret_cast<uint8_t *>(clean_addr);
  uint64_t dst_addr = reinterpret_cast<uint64_t>(buf + app_rx_buf->tail * 64);

  // Copy packet to application buffer.
  dma_write *data_dma = new dma_write(this, dst_addr, aligned_len, data, log);
  data_dma->Issue();

  uint32_t old_tail = app_rx_buf->tail;
  app_rx_buf->tail = (app_rx_buf->tail + flits) % ENSO_PIPE_SIZE;

  if (old_tail == app_rx_buf->head) {
    // Buffer was empty, send notification.
    send_rx_notif(pipe_id);
  }
}

void enso_bm::SendEthPacket(const uint8_t *data, size_t len) {
#ifdef DEBUG_DEV
  log << "TX: sending packet to ethernet len=" << len << logger::endl;
#endif
  stats_.tx_pkts++;
  runner_->EthSend(data, len);
}

void enso_bm::send_rx_notif(uint32_t queue) {
  struct ring_buf *rx_buf = &rx_bufs_[queue];
  // Get notif_queue_id as it was sent in the mmio_write for rx_mem_low
  // for this enso pipe.
  uint32_t notif_queue_id =
      reinterpret_cast<uint64_t>(rx_buf->buf) & (MAX_NB_APPS - 1);
  struct ring_buf *app_rx_notif_buf = &rx_notif_bufs_[notif_queue_id];

  // Check if there is space in the notification buffer.
  uint32_t nb_free_slots =
      (app_rx_notif_buf->head - app_rx_notif_buf->tail - 1) % ENSO_PIPE_SIZE;

  if (nb_free_slots == 0) {
    // Buffer is full, drop notification.
#ifdef DEBUG_DEV
    log << "RX notification buffer is full." << logger::endl;
#endif
    stats_.notif_drops++;
    return;
  }

  // Send notification.
  rx_notification notif;
  notif.signal = 1;
  notif.queue_id = queue;
  notif.tail = rx_buf->tail;
  rx_notification *notif_buf =
      reinterpret_cast<rx_notification *>(app_rx_notif_buf->buf);
  rx_notification *hwb_addr = &notif_buf[app_rx_notif_buf->tail];

  dma_write *dma = new dma_write(this, reinterpret_cast<uint64_t>(hwb_addr),
                                 sizeof(rx_notification),
                                 reinterpret_cast<uint8_t *>(&notif), log);
  dma->Issue();

  app_rx_notif_buf->tail = (app_rx_notif_buf->tail + 1) % NOTIFICATION_BUF_SIZE;
}

void enso_bm::process_tx_notif(tx_notification *notification,
                               uint64_t completion_addr) {
  int signal = notification->signal;

  // Turn TX notification into completion notification.
  notification->signal = 0;
  dma_write *completion_dma =
      new dma_write(this, completion_addr, sizeof(tx_notification),
                    reinterpret_cast<uint8_t *>(notification), log);

  if (signal == 1) {  // Data.
    dma_read_data *dma = new dma_read_data(
        this, notification->phys_addr,
        static_cast<size_t>(notification->length), completion_dma, log);
    dma->Issue();
  } else if (signal == 2) {  // Configuration.
    process_config(reinterpret_cast<config::config *>(notification));
    completion_dma->Issue();
  } else {
    log << "Invalid TX notification signal: " << signal << logger::endl;
    delete completion_dma;
    return;
  }
}

void enso_bm::process_config(config::config *config) {
  uint64_t config_id = config->config_id;
  switch (config_id) {
    case config::FLOW_TABLE_CONFIG_ID:
      process_flow_table_config(reinterpret_cast<config::flow_table *>(config));
      break;
    case config::TIMESTAMP_CONFIG_ID:
      process_timestamp_config(reinterpret_cast<config::timestamp *>(config));
      break;
    case config::RATE_LIMIT_CONFIG_ID:
      process_rate_limit_config(reinterpret_cast<config::rate_limit *>(config));
      break;
    case config::FALLBACK_QUEUES_CONFIG_ID:
      process_fallback_queues_config(
          reinterpret_cast<config::fallback_queue *>(config));
      break;
    default:
      log << "Invalid configuration ID: " << config_id << logger::endl;
      break;
  }
}

void enso_bm::process_flow_table_config(config::flow_table *flow_table) {
  uint16_t dst_port = flow_table->dst_port;
  uint16_t src_port = flow_table->src_port;
  uint32_t dst_ip = flow_table->dst_ip;
  uint32_t src_ip = flow_table->src_ip;
  uint32_t enso_pipe_id = flow_table->enso_pipe_id;

  rx_pipeline_.add_flow_table_entry(dst_port, src_port, dst_ip, src_ip,
                                    enso_pipe_id);
}

void enso_bm::process_timestamp_config(
    [[maybe_unused]] config::timestamp *timestamp) {
  // TODO(sadok): Implement timestamping.
}

void enso_bm::process_rate_limit_config(
    [[maybe_unused]] config::rate_limit *queue) {
  // TODO(sadok): Implement rate limiting.
}

void enso_bm::process_fallback_queues_config(
    [[maybe_unused]] config::fallback_queue *fallback_queues) {
  rx_pipeline_.enable_rr = fallback_queues->enable_rr;
  rx_pipeline_.set_fallback_queues(fallback_queues->nb_fallback_queues,
                                   fallback_queues->fallback_queue_mask);
}

void enso_bm::reset() {
  rx_pipeline_.reset();
  tx_pipeline_.reset();

  rx_bufs_ = {0};
  rx_notif_bufs_ = {0};
  tx_notif_bufs_ = {0};
  stats_ = {0};
}

}  // namespace enso_bm

class enso_factory : public nicbm::MultiNicRunner::DeviceFactory {
 public:
  nicbm::Runner::Device &create() override {
    return *new enso_bm::enso_bm;
  }
};

int main(int argc, char *argv[]) {
  enso_factory fact;
  nicbm::MultiNicRunner mr(fact);
  return mr.RunMain(argc, argv);
}
