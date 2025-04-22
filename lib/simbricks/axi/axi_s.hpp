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

 #ifndef SIMBRICKS_AXI_STREAM_HH_
 #define SIMBRICKS_AXI_STREAM_HH_
 
 #include <stddef.h>
 
 #include <algorithm>
 #include <array>
 #include <exception>
 #include <type_traits>
 
 #include "lib/utils/log.h"
 #include "lib/utils/util.hpp"
 
 #define AXIS_DEBUG 0
 
 namespace simbricks {
 
 namespace core {
 
 template <size_t BufferSize = 2048,
           typename = typename std::enable_if_t<
               (BufferSize >= 2048) and simbricks::isPowerOfTwo(BufferSize)>>
 class ManagerBuffer {
   std::array<uint8_t, BufferSize> packet_buf_{0};
   size_t packet_len_ = 0;
   size_t read_offset_ = 0;
 
  public:
   void reset(const uint8_t *data, size_t len) noexcept {
     std::copy(data, data + len, packet_buf_.data());
     packet_len_ = len;
     read_offset_ = 0;
   }
 
   [[nodiscard]] bool done() const noexcept {
     return read_offset_ >= packet_len_;
   }
 
   [[nodiscard]] bool empty() const noexcept {
     return packet_len_ == 0;
   }
 
   uint8_t read() noexcept {
     if (done()) {
       sim_log::LogError(
           "simbricks::core::ManagerBuffer::read try reading past packet\n");
       std::terminate();
     }
     uint8_t res = packet_buf_[read_offset_];
     ++read_offset_;
     return res;
   }
 };
 
 template <size_t BufferSize = 2048,
           typename = typename std::enable_if_t<
               (BufferSize >= 2048) and simbricks::isPowerOfTwo(BufferSize)>>
 class SubordinateBuffer {
   std::array<uint8_t, BufferSize> packet_buf_{0};
   size_t packet_len_ = 0;
   bool done_ = 0;
 
  public:
   [[nodiscard]] bool full() const noexcept {
     return packet_len_ == BufferSize;
   }
 
   [[nodiscard]] bool done() const noexcept {
     return done_;
   }
 
   void setDone() noexcept {
     done_ = true;
   }
 
   void setNextByte(uint8_t by) {
     if (full()) {
       sim_log::LogError(
           "simbricks::core::SubordinateBuffer::setNextByte past packet "
           "buffer\n");
       std::terminate();
     }
     packet_buf_[packet_len_] = by;
     ++packet_len_;
   }
 
   void assign(uint8_t *data, size_t *len) noexcept {
     std::copy(packet_buf_.data(), packet_buf_.data() + packet_len_, data);
     *len = packet_len_;
     packet_len_ = 0;
     done_ = false;
   }
 };
 
 }  // namespace core
 
 template <size_t DataWidthBytes = 4, size_t AmountSlots = 32,
           size_t BufferSize = 2048,
           typename = typename std::enable_if_t<
               (DataWidthBytes >= 1) and (DataWidthBytes <= 128) and
               simbricks::isPowerOfTwo(DataWidthBytes) and (AmountSlots > 0)>>
 class AXISManager {
   /**
    * TVALID indicates the Transmitter is driving a valid transfer. A transfer
    * takes place when both TVALID and TREADY are asserted.
    */
   uint8_t &tvalid_;
   /**
    * TREADY indicates that a Receiver can
    * accept a transfer.
    */
   const uint8_t &tready_;
   /**
    * TDATA is the primary payload used to provide the data that is passing
    * across the interface. TDATA_WIDTH must be an integer number of bytes and
    * is recommended to be 8, 16, 32, 64, 128, 256, 512 or 1024-bits.
    */
   uint8_t *const tdata_;
 
   /**
    * TSTRB is the byte qualifier that indicates whether the content of the
    * associated byte of TDATA is processed as a data byte or a position byte
    */
   // const uint8_t *const tstrb_;
   // const size_t kStrbWidth = DataWidthBytes / 8;
   /**
    * TKEEP is the byte qualifier that indicates whether content of the
    * associated byte of TDATA is processed as part of the data stream.
    */
   uint8_t *const tkeep_;
   const size_t kKeepWidth = DataWidthBytes / 8;
   /**
    * TLAST indicates the boundary of a packet
    */
   uint8_t &tlast_;
   /**
    * TID is a data stream identifier.
    **/
   // TODO: TID Width
   // const uint8_t *const tid_;
   /**
    * TDEST provides routing information for the data stream.
    */
   // TODO: TDEST_WIDTH
   // const uint8_t *const tdest_;
   /**
    * TUSER is a user-defined sideband information that can be transmitted along
    * the data stream. TUSER_WIDTH is recommended to be an integer multiple of
    * TDATA_WIDTH/8.
    */
   // TODO: TUSER_WIDTH
   const uint8_t *const tuser_;
   /**
    * TWAKEUP identifies any activity associated with AXI-Stream interface.
    */
   // uint8_t &twakeup_;
   /**
    * Packet ring-buffer for storing packets that shall be sent
    */
   std::array<core::ManagerBuffer<BufferSize>, AmountSlots> buffer_ring_;
   size_t write_index_ = 0;
   size_t read_index_ = 0;
   size_t cur_size_ = 0;
 
   void move_read_head() noexcept {
     if (not buffer_ring_[read_index_].done()) {
       sim_log::LogError(
           "simbricks::core::AXISManager::move_read_head cant move read head, "
           "current buffer is not done yet\n");
       std::terminate();
     }
     read_index_ = (read_index_ + 1) % AmountSlots;
     --cur_size_;
   }
 
   bool data_transfer_can_happen() const {
     return tready_;
   }
 
   void setIndex(uint8_t *const bitmap, size_t index) const {
     const size_t byte_index = index / 8;
     const size_t bit_index = index % 8;
     bitmap[byte_index] = bitmap[byte_index] | (1 << bit_index);
   }
 
   void reset(uint8_t *bitmap, size_t size) {
     for (size_t index = 0; index < size; index++) {
       bitmap[index] = 0;
     }
   }
 
  public:
   explicit AXISManager(uint8_t &tvalid, const uint8_t &tready,
                        uint8_t *const tdata,
                        // const uint8_t *const tstrb,
                        uint8_t *const tkeep, uint8_t &tlast,
                        // const uint8_t *const tid,
                        // const uint8_t *const tdest,
                        const uint8_t *const tuser
                        // , uint8_t &twakeup
                        )
       : tvalid_(tvalid),
         tready_(tready),
         tdata_(tdata),
         // tstrb_(tstrb),
         tkeep_(tkeep),
         tlast_(tlast),
         // tid_(tid),
         // tdest_(tdest),
         tuser_(tuser)
   //, twakeup_(twakeup)
   {
   }
 
   [[nodiscard]] bool full() const noexcept {
 #ifdef AXIS_DEBUG
     sim_log::LogInfo("AXISManager::full: cur_size_=%lu, AmountSlots=%lu\n",
                      cur_size_, AmountSlots);
 #endif
     return cur_size_ >= AmountSlots;
   }
 
   [[nodiscard]] bool empty() const noexcept {
     return cur_size_ == 0;
   }
 
   /**
    * When implementing the exchange of SimBricks messages within a Simulators
    * adapter, this method shall be called if e.g. the AXI stream interface
    * receives a packet. This can e.g. happen if a NIC receives a network packet.
    */
   void read(const uint8_t *data, size_t len) noexcept {
 #ifdef AXIS_DEBUG
     sim_log::LogInfo("AXISManager read\n");
 #endif
 
     if (data == nullptr or len == 0) {
       sim_log::LogError(
           "simbricks::core::AXISManager::read no packet data given\n");
       std::terminate();
     }
     if (full()) {
       sim_log::LogError(
           "simbricks::core::AXISManager::read drop packet as ring buffer is "
           "full");
       std::terminate();
     }
 
     auto &buffer = buffer_ring_[write_index_];
     buffer.reset(data, len);
     ++cur_size_;
     write_index_ = (write_index_ + 1) % AmountSlots;
   }
 
   void step() noexcept {
 #ifdef AXIS_DEBUG
     // sim_log::LogInfo("AXISManager step\n");
 #endif
 
     if (empty() or buffer_ring_[read_index_].empty()) {
       // std::cout << "no data to send" << std::endl;
       // no data to send
       tvalid_ = 0;
       tlast_ = 0;
       return;
     }
 
     // TODO: no need to wait for tready here in principle
     if (not buffer_ring_[read_index_].done() and not tready_) {
 #ifdef AXIS_DEBUG
       sim_log::LogInfo(
           "AXISManager cannot put out packet data, no tready signal\n");
 #endif
       // no ready signal available
       return;
     }
 
     if (buffer_ring_[read_index_].done()) {
 #ifdef AXIS_DEBUG
       sim_log::LogInfo("AXISManager done with packet\n");
 #endif
       // done with packet
       tvalid_ = 0;
       tlast_ = 0;
       move_read_head();
       return;
     }
 
     // put out more packet data
 #ifdef AXIS_DEBUG
     sim_log::LogInfo("AXISManager put out more packet data\n");
 #endif
     reset(tkeep_, kKeepWidth);
     auto &buffer = buffer_ring_[read_index_];
     for (size_t index = 0; index < DataWidthBytes and not buffer.done();
          index++) {
       tdata_[index] = buffer.read();
       setIndex(tkeep_, index);
     }
     tvalid_ = 1;
     tlast_ = buffer.done();
   }
 };
 
 template <
     size_t DataWidthBytes = 4, size_t PacketBufSize = 2048,
     typename = typename std::enable_if_t<
         (DataWidthBytes >= 1) and simbricks::isPowerOfTwo(DataWidthBytes) and
         (PacketBufSize >= 2048) and simbricks::isPowerOfTwo(PacketBufSize) and
         (DataWidthBytes <= 128)>>
 class AXISSubordinate {
   /**
    * TVALID indicates the Transmitter is driving a valid transfer. A transfer
    * takes place when both TVALID and TREADY are asserted.
    */
   const uint8_t &tvalid_;
   /**
    * TREADY indicates that a Receiver can
    * accept a transfer.
    */
   uint8_t &tready_;
   /**
    * TDATA is the primary payload used to provide the data that is passing
    * across the interface. TDATA_WIDTH must be an integer number of bytes and
    * is recommended to be 8, 16, 32, 64, 128, 256, 512 or 1024-bits.
    */
   const uint8_t *const tdata_;
 
   /**
    * TSTRB is the byte qualifier that indicates whether the content of the
    * associated byte of TDATA is processed as a data byte or a position byte
    */
   // const uint8_t *const tstrb_;
   // const size_t kStrbWidth = DataWidthBytes / 8;
   /**
    * TKEEP is the byte qualifier that indicates whether content of the
    * associated byte of TDATA is processed as part of the data stream.
    */
   const uint8_t *const tkeep_;
   const size_t kKeepWidth = DataWidthBytes / 8;
   /**
    * TLAST indicates the boundary of a packet
    */
   uint8_t &tlast_;
   /**
    * TID is a data stream identifier.
    **/
   // TODO: TID Width
   // const uint8_t *const tid_;
   /**
    * TDEST provides routing information for the data stream.
    */
   // TODO: TDEST_WIDTH
   // const uint8_t *const tdest_;
   /**
    * TUSER is a user-defined sideband information that can be transmitted along
    * the data stream. TUSER_WIDTH is recommended to be an integer multiple of
    * TDATA_WIDTH/8.
    */
   // TODO: TUSER_WIDTH
   const uint8_t *const tuser_;
   /**
    * TWAKEUP identifies any activity associated with AXI-Stream interface.
    */
   // const uint8_t &twakeup_;
   /**
    * Packet Buffer to store the packet that is to be forwarded.
    */
   core::SubordinateBuffer<PacketBufSize> packet_buf_;
 
   bool data_transfer_can_happen() const {
     return tvalid_ and tready_;
   }
 
   bool isSet(const uint8_t *const bitmap, size_t index) const {
     if (index >= DataWidthBytes) {
       sim_log::LogError(
           "AXISSubordinate::isSet: index %zu larger then DataWidthBytes %zu",
           index, DataWidthBytes);
       std::terminate();
     }
     const size_t int_pos = index / 8;
     const size_t bit_pos = index % 8;
     const uint8_t b = bitmap[int_pos];
     return static_cast<bool>(b & (1 << bit_pos));
   }
 
  public:
   explicit AXISSubordinate(const uint8_t &tvalid, uint8_t &tready,
                            const uint8_t *const tdata,
                            // const uint8_t *const tstrb,
                            const uint8_t *const tkeep, uint8_t &tlast,
                            // const uint8_t *const tid,
                            // const uint8_t *const tdest,
                            const uint8_t *const tuser
                            // , const uint8_t &twakeup
                            )
       : tvalid_(tvalid),
         tready_(tready),
         tdata_(tdata),
         // tstrb_(tstrb),
         tkeep_(tkeep),
         tlast_(tlast),
         // tid_(tid),
         // tdest_(tdest),
         tuser_(tuser)
   //, twakeup_(twakeup)
   {
   }
 
   bool is_packet_done() const {
     return packet_buf_.done();
   }
 
   void step() noexcept {
     tready_ = 1;
     if (not data_transfer_can_happen()) {
       return;
     }
 
     if (packet_buf_.done() or packet_buf_.full()) {
       sim_log::LogError(
           "simbricks::core::AXISSubordinate::step cannot step, finished not "
           "yet transmitted packet buffer present\n");
       std::terminate();
     }
 
 #ifdef AXIS_DEBUG
     sim_log::LogInfo("AXISSubordinate::step: set Next Bytes\n");
 #endif
     for (size_t index = 0; index < DataWidthBytes; index++) {
       if (not isSet(tkeep_, index)) {
         continue;
       }
       packet_buf_.setNextByte(tdata_[index]);
     }
 
     if (static_cast<bool>(tlast_)) {
 #ifdef AXIS_DEBUG
       sim_log::LogInfo(
           "AXISSubordinate::step: tlast was set, transmittted packet\n");
 #endif
       packet_buf_.setDone();
     }
   }
 
   /**
    * When implementing the exchange of SimBricks messages within a Simulators
    * adapter,this method shall be called to copy the packet data into the
    * SimBricks message buffer.
    */
   void write(uint8_t *destination, size_t *len) noexcept {
 #ifdef AXIS_DEBUG
     sim_log::LogInfo("AXISSubordinate write\n");
 #endif
 
     if (not packet_buf_.done()) {
       sim_log::LogError(
           "simbricks::core::AXISSubordinate::write cannot write, packet within "
           "buffer isn't done yet\n");
       std::terminate();
     }
     packet_buf_.assign(destination, len);
   }
 };
 
 }  // namespace simbricks
 
 #endif  // SIMBRICKS_AXI_STREAM_HH_