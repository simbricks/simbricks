/*
 * Copyright 2022 Max Planck Institute for Software Systems, and
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

#ifndef PORTS_H_
#define PORTS_H_

#include <stdint.h>

#include <simbricks/base/cxxatomicfix.h>
extern "C" {
#include <simbricks/network/if.h>
}

extern uint64_t sync_period;
extern uint64_t eth_latency;
extern int sync_mode;

/** Abstract base switch port */
class Port {
 public:
  enum RxPollState {
    kRxPollSuccess = 0,
    kRxPollFail = 1,
    kRxPollSync = 2,
  };

  virtual ~Port() = default;

  virtual bool Connect(const char *path, int sync) = 0;
  virtual bool IsSync() = 0;
  virtual void Sync(uint64_t cur_ts) = 0;
  virtual uint64_t NextTimestamp() = 0;
  virtual enum RxPollState RxPacket(
      const void *& data, size_t &len, uint64_t cur_ts) = 0;
  virtual void RxDone() = 0;
  virtual bool TxPacket(const void *data, size_t len, uint64_t cur_ts) = 0;
};


/** Normal network switch port (conneting to a NIC) */
class NetPort : public Port {
 protected:
  struct SimbricksBaseIfParams *params_;
  struct SimbricksNetIf netifObj_;
  struct SimbricksNetIf *netif_;
  volatile union SimbricksProtoNetMsg *rx_;
  int sync_;

 public:
  explicit NetPort(struct SimbricksBaseIfParams *params) : params_(params),
      netif_(&netifObj_), rx_(nullptr), sync_(0) {
    memset(&netifObj_, 0, sizeof(netifObj_));
  }

  NetPort(const NetPort &other) : netifObj_(other.netifObj_),
      netif_(&netifObj_), rx_(other.rx_), sync_(other.sync_) {}

  bool Connect(const char *path, int sync) override {
    sync_ = sync;
    return SimbricksNetIfInit(netif_, params_, path, &sync_) == 0;
  }

  bool IsSync() override {
    return sync_;
  }

  void Sync(uint64_t cur_ts) override {
    while (SimbricksNetIfOutSync(netif_, cur_ts)) {}
  }

  uint64_t NextTimestamp() override {
    return SimbricksNetIfInTimestamp(netif_);
  }

  enum RxPollState RxPacket(
      const void *& data, size_t &len, uint64_t cur_ts) override {
    assert(rx_ == nullptr);

    rx_ = SimbricksNetIfInPoll(netif_, cur_ts);
    if (!rx_)
      return kRxPollFail;

    uint8_t type = SimbricksNetIfInType(netif_, rx_);
    if (type == SIMBRICKS_PROTO_NET_MSG_PACKET) {
      data = (const void *)rx_->packet.data;
      len = rx_->packet.len;
      return kRxPollSuccess;
    } else if (type == SIMBRICKS_PROTO_MSG_TYPE_SYNC) {
      return kRxPollSync;
    } else {
      fprintf(stderr, "switch_pkt: unsupported type=%u\n", type);
      abort();
    }
  }

  void RxDone() override {
    assert(rx_ != nullptr);

    SimbricksNetIfInDone(netif_, rx_);
    rx_ = nullptr;
  }

  bool TxPacket(
      const void *data, size_t len, uint64_t cur_ts) override {
    volatile union SimbricksProtoNetMsg *msg_to =
      SimbricksNetIfOutAlloc(netif_, cur_ts);
    if (!msg_to && !sync_) {
      return false;
    } else if (!msg_to && sync_) {
      while (!msg_to)
        msg_to = SimbricksNetIfOutAlloc(netif_, cur_ts);
    }
    volatile struct SimbricksProtoNetMsgPacket *rx;
    rx = &msg_to->packet;
    rx->len = len;
    rx->port = 0;
    memcpy((void *)rx->data, data, len);

    SimbricksNetIfOutSend(netif_, msg_to, SIMBRICKS_PROTO_NET_MSG_PACKET);
    return true;
  }
};

#endif  // PORTS_H_
