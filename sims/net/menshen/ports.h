#ifndef NET_MENSHEN_PORTS_H_
#define NET_MENSHEN_PORTS_H_

#include <stdint.h>

#include <simbricks/proto/base.h>
#include <simbricks/proto/network.h>
extern "C" {
#include <simbricks/netif/netif.h>
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
  virtual void AdvanceEpoch(uint64_t cur_ts) = 0;
  virtual uint64_t NextTimestamp() = 0;
  virtual enum RxPollState RxPacket(
      const void *& data, size_t &len, uint64_t cur_ts) = 0;
  virtual void RxDone() = 0;
  virtual bool TxPacket(const void *data, size_t len, uint64_t cur_ts) = 0;
};


/** Normal network switch port (conneting to a NIC) */
class NetPort : public Port {
 protected:
  struct SimbricksNetIf netif_;
  volatile union SimbricksProtoNetD2N *rx_;
  int sync_;

 public:
  NetPort() : rx_(nullptr), sync_(0) {
    memset(&netif_, 0, sizeof(netif_));
  }

  NetPort(const NetPort &other) : netif_(other.netif_), rx_(other.rx_),
      sync_(other.sync_) {}

  virtual bool Connect(const char *path, int sync) override {
    sync_ = sync;
    return SimbricksNetIfInit(&netif_, path, &sync_) == 0;
  }

  virtual bool IsSync() override {
    return sync_;
  }

  virtual void Sync(uint64_t cur_ts) override {
    while (SimbricksNetIfN2DSync(&netif_, cur_ts, eth_latency, sync_period,
                              sync_mode));
  }

  virtual void AdvanceEpoch(uint64_t cur_ts) override {
    SimbricksNetIfAdvanceEpoch(cur_ts, sync_period, sync_mode);
  }

  virtual uint64_t NextTimestamp() override {
    return SimbricksNetIfD2NTimestamp(&netif_);
  }

  virtual enum RxPollState RxPacket(
      const void *& data, size_t &len, uint64_t cur_ts) override {
    assert(rx_ == nullptr);

    rx_ = SimbricksNetIfD2NPoll(&netif_, cur_ts);
    if (!rx_)
      return kRxPollFail;

    uint8_t type = rx_->dummy.own_type & SIMBRICKS_PROTO_NET_D2N_MSG_MASK;
    if (type == SIMBRICKS_PROTO_NET_D2N_MSG_SEND) {
      data = (const void *)rx_->send.data;
      len = rx_->send.len;
      return kRxPollSuccess;
    } else if (type == SIMBRICKS_PROTO_NET_D2N_MSG_SYNC) {
      return kRxPollSync;
    } else {
      fprintf(stderr, "switch_pkt: unsupported type=%u\n", type);
      abort();
    }
  }

  virtual void RxDone() override {
    assert(rx_ != nullptr);

    SimbricksNetIfD2NDone(&netif_, rx_);
    rx_ = nullptr;
  }

  virtual bool TxPacket(
      const void *data, size_t len, uint64_t cur_ts) override {
    volatile union SimbricksProtoNetN2D *msg_to =
      SimbricksNetIfN2DAlloc(&netif_, cur_ts, eth_latency);
    if (!msg_to && !sync_) {
      return false;
    } else if (!msg_to && sync_) {
      while (!msg_to)
        msg_to = SimbricksNetIfN2DAlloc(&netif_, cur_ts, eth_latency);
    }
    volatile struct SimbricksProtoNetN2DRecv *rx;
    rx = &msg_to->recv;
    rx->len = len;
    rx->port = 0;
    memcpy((void *)rx->data, data, len);

    // WMB();
    rx->own_type =
        SIMBRICKS_PROTO_NET_N2D_MSG_RECV | SIMBRICKS_PROTO_NET_N2D_OWN_DEV;
    return true;
  }
};

#endif  // NET_MENSHEN_PORTS_H_