#ifndef NET_MENSHEN_PORTS_H_
#define NET_MENSHEN_PORTS_H_

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
  NetPort(struct SimbricksBaseIfParams *params) : params_(params),
      netif_(&netifObj_), rx_(nullptr), sync_(0) {
    memset(&netifObj_, 0, sizeof(netifObj_));
  }

  NetPort(const NetPort &other) : netifObj_(other.netifObj_),
      netif_(&netifObj_), rx_(other.rx_), sync_(other.sync_) {}

  virtual bool Connect(const char *path, int sync) override {
    sync_ = sync;
    return SimbricksNetIfInit(netif_, params_, path, &sync_) == 0;
  }

  virtual bool IsSync() override {
    return sync_;
  }

  virtual void Sync(uint64_t cur_ts) override {
    while (SimbricksNetIfOutSync(netif_, cur_ts));
  }

  virtual uint64_t NextTimestamp() override {
    return SimbricksNetIfInTimestamp(netif_);
  }

  virtual enum RxPollState RxPacket(
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

  virtual void RxDone() override {
    assert(rx_ != nullptr);

    SimbricksNetIfInDone(netif_, rx_);
    rx_ = nullptr;
  }

  virtual bool TxPacket(
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

#endif  // NET_MENSHEN_PORTS_H_