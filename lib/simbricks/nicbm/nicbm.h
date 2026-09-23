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

#ifndef SIMBRICKS_NICBM_NICBM_H_
#define SIMBRICKS_NICBM_NICBM_H_

#include <cassert>
#include <cstring>
#include <deque>
#include <set>

#include <simbricks/base/cxxatomicfix.h>
extern "C" {
#include <simbricks/nicif/nicif.h>
#include <simbricks/parser/parser.h>
}

#include <simbricks/utils/log.h>
namespace nicbm {

static const size_t kMaxDmaLen = 2048;

class DMAOp {
 public:
  virtual ~DMAOp() = default;
  bool write_;
  uint64_t dma_addr_;
  size_t len_;
  void *data_;
};

class TimedEvent {
 public:
  TimedEvent() : time_(0), priority_(0) {
  }
  virtual ~TimedEvent() = default;
  uint64_t time_;
  int priority_;
};

/**
 * Per-process debug log, enabled with a leading `--debug-log=PATH` argument.
 * One line per PCIe/Ethernet message the runner sends or receives, per DMA
 * operation and interrupt, plus whatever the device model reports through
 * `Runner::Debug()`. Parsed by simbricks-trace; format:
 *
 *   # simbricks-debug nicbm 1
 *   # runner <idx> pci=<socket> eth=<socket> start=<ts> mac=<hex>
 *   <main_time> <runner idx> <kind> <fields...>
 *
 * PATH may be a FIFO. The log is shared by all runners of a process (they are
 * cooperative fibers, so no locking is needed).
 */
class DebugLog {
 public:
  static DebugLog *Open(const char *path);
  ~DebugLog();

  void RunnerInfo(unsigned idx, const char *pci_sock, const char *eth_sock,
                  uint64_t start_ts, uint64_t mac);
  void Emit(uint64_t ts, unsigned runner, const char *kind, const char *fmt,
            ...) __attribute__((format(printf, 5, 6)));
  void Flush();

 protected:
  explicit DebugLog(FILE *file) : file_(file) {
  }
  FILE *file_;
};

/**
 * The Runner drives the main simulation loop. It's initialized with a reference
 * to a device it should manage, and then once `runMain` is called, it will
 * start interacting with the PCI and Ethernet queue and forwarding calls to the
 * device as needed.
 * */
class Runner {
 public:
  class Device {
   public:
    Runner *runner_;

   protected:
    bool int_intx_en_;
    bool int_msi_en_;
    bool int_msix_en_;

   public:
    /**
     * Initialize device specific parameters (pci dev/vendor id,
     * BARs etc. in intro struct.
     */
    virtual void SetupIntro(struct SimbricksProtoPcieDevIntro &di) = 0;

    /**
     * execute a register read from `bar`:`addr` of length `len`.
     * Should store result in `dest`.
     */
    virtual void RegRead(uint8_t bar, uint64_t addr, void *dest, size_t len) = 0;

    /**
     * execute a register write to `bar`:`addr` of length `len`,
     * with the data in `src`.
     */
    virtual void RegWrite(uint8_t bar, uint64_t addr, const void *src, size_t len) = 0;

    /**
     * the previously issued DMA operation `op` completed.
     */
    virtual void DmaComplete(DMAOp &op) = 0;

    /**
     * A packet has arrived on the wire, of length `len` with
     * payload `data`.
     */
    virtual void EthRx(uint8_t port, const void *data, size_t len) = 0;

    /**
     * A timed event is due.
     */
    virtual void Timed(TimedEvent &te);

    /**
     * Device control update
     */
    virtual void DevctrlUpdate(struct SimbricksProtoPcieH2DDevctrl &devctrl);
  };

 protected:
  struct EventCmp {
    bool operator()(TimedEvent *a, TimedEvent *b) const {
      return a->time_ < b->time_ || (a->time_ == b->time_ && a->priority_ < b->priority_);
    }
  };

  uint64_t main_time_;
  Device &dev_;
  std::multiset<TimedEvent *, EventCmp> events_;
  std::deque<DMAOp *> dma_queue_;
  size_t dma_pending_;
  uint64_t mac_addr_;
  struct SimbricksBaseIfParams pcieParams_;
  struct SimbricksBaseIfParams netParams_;
  const char *shmPath_;
  struct SimbricksNicIf nicif_;
  struct SimbricksProtoPcieDevIntro dintro_;

  struct SimbricksAdapterParams *pcieAdapterParams_;
  struct SimbricksAdapterParams *netAdapterParams_;

  sim_log::LogPtT log_ = sim_log::Log::createLog();
  DebugLog *debug_log_ = nullptr;
  bool debug_log_owned_ = false;
  unsigned runner_idx_ = 0;
  uint64_t heartbeat_ts_ = 0;  // last `hb` line written to the debug log

  volatile union SimbricksProtoPcieD2H *D2HAlloc();
  volatile union SimbricksProtoNetMsg *D2NAlloc();

  void H2DRead(volatile struct SimbricksProtoPcieH2DRead *read);
  void H2DWrite(volatile struct SimbricksProtoPcieH2DWrite *write, bool posted);
  void H2DReadcomp(volatile struct SimbricksProtoPcieH2DReadcomp *rc);
  void H2DWritecomp(volatile struct SimbricksProtoPcieH2DWritecomp *wc);
  void H2DDevctrl(volatile struct SimbricksProtoPcieH2DDevctrl *dc);
  void PollH2D();

  void EthRecv(volatile struct SimbricksProtoNetMsgPacket *packetl);
  void PollN2D();

  bool EventNext(uint64_t &retval);
  void EventTrigger();

  void DmaDo(DMAOp &op);
  void DmaTrigger();

  virtual void YieldPoll();
  virtual int NicIfInit();

 public:
  explicit Runner(Device &dev_);
  virtual ~Runner();

  /** Parse command line arguments. */
  int ParseArgs(int argc, char *argv[]);

  /** Run the simulation */
  int RunMain();

  /* these three are for `Runner::Device`. */
  void IssueDma(DMAOp &op);
  void MsiIssue(uint8_t vec);
  void MsiXIssue(uint8_t vec);
  void IntXIssue(bool level);
  void EthSend(const void *data, size_t len);

  void EventSchedule(TimedEvent &evt);
  void EventCancel(TimedEvent &evt);

  uint64_t TimePs() const;
  uint64_t GetMacAddr() const;

  /** Attach a debug log (shared between runners of a multi-NIC process). */
  void SetDebugLog(DebugLog *log, unsigned idx, bool owned = false);
  bool DebugEnabled() const {
    return debug_log_ != nullptr;
  }
  void FlushDebugLog() {
    if (debug_log_)
      debug_log_->Flush();
  }
  /** Device models report internal events with this (no-op unless enabled). */
  void Debug(const char *kind, const char *fmt, ...)
      __attribute__((format(printf, 3, 4)));
  /**
   * Print baseif info
   *
   */
  void PrintBaseIfInfo(void);
};

/**
 * Very simple device that just has one register size.
 */
template <class TReg = uint32_t>
class SimpleDevice : public Runner::Device {
 public:
  virtual TReg RegRead(uint8_t bar, uint64_t addr) = 0;
  virtual void RegWrite(uint8_t bar, uint64_t addr, TReg val) = 0;

  void RegRead(uint8_t bar, uint64_t addr, void *dest, size_t len) override {
    assert(len == sizeof(TReg));
    TReg r = RegRead(bar, addr);
    memcpy(dest, &r, sizeof(r));
  }

  void RegWrite(uint8_t bar, uint64_t addr, const void *src, size_t len) override {
    assert(len == sizeof(TReg));
    TReg r;
    memcpy(&r, src, sizeof(r));
    RegWrite(bar, addr, r);
  }
};
}  // namespace nicbm

#endif  // SIMBRICKS_NICBM_NICBM_H_
