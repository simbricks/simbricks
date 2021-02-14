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

extern "C" {
#include <simbricks/nicif/nicsim.h>
}

namespace nicbm {

static const size_t MAX_DMA_LEN = 2048;

class DMAOp {
 public:
  virtual ~DMAOp() {
  }
  bool write;
  uint64_t dma_addr;
  size_t len;
  void *data;
};

class TimedEvent {
 public:
  virtual ~TimedEvent() {
  }
  uint64_t time;
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
   protected:
    bool int_intx_en;
    bool int_msi_en;
    bool int_msix_en;

   public:
    /**
     * Initialize device specific parameters (pci dev/vendor id,
     * BARs etc. in intro struct.
     */
    virtual void setup_intro(struct SimbricksProtoPcieDevIntro &di) = 0;

    /**
     * execute a register read from `bar`:`addr` of length `len`.
     * Should store result in `dest`.
     */
    virtual void reg_read(uint8_t bar, uint64_t addr, void *dest,
                          size_t len) = 0;

    /**
     * execute a register write to `bar`:`addr` of length `len`,
     * with the data in `src`.
     */
    virtual void reg_write(uint8_t bar, uint64_t addr, const void *src,
                           size_t len) = 0;

    /**
     * the previously issued DMA operation `op` completed.
     */
    virtual void dma_complete(DMAOp &op) = 0;

    /**
     * A packet has arrived on the wire, of length `len` with
     * payload `data`.
     */
    virtual void eth_rx(uint8_t port, const void *data, size_t len) = 0;

    /**
     * A timed event is due.
     */
    virtual void timed_event(TimedEvent &ev);

    /**
     * Device control update
     */
    virtual void devctrl_update(struct SimbricksProtoPcieH2DDevctrl &devctrl);
  };

 protected:
  struct event_cmp {
    bool operator()(TimedEvent *a, TimedEvent *b) {
      return a->time < b->time;
    }
  };

  Device &dev;
  std::set<TimedEvent *, event_cmp> events;
  std::deque<DMAOp *> dma_queue;
  size_t dma_pending;
  uint64_t mac_addr;
  struct nicsim_params nsparams;
  struct SimbricksProtoPcieDevIntro dintro;

  volatile union SimbricksProtoPcieD2H *d2h_alloc(void);
  volatile union SimbricksProtoNetD2N *d2n_alloc(void);

  void h2d_read(volatile struct SimbricksProtoPcieH2DRead *read);
  void h2d_write(volatile struct SimbricksProtoPcieH2DWrite *write);
  void h2d_readcomp(volatile struct SimbricksProtoPcieH2DReadcomp *rc);
  void h2d_writecomp(volatile struct SimbricksProtoPcieH2DWritecomp *wc);
  void h2d_devctrl(volatile struct SimbricksProtoPcieH2DDevctrl *dc);
  void poll_h2d();

  void eth_recv(volatile struct SimbricksProtoNetN2DRecv *recv);
  void poll_n2d();

  bool event_next(uint64_t &retval);
  void event_trigger();

  void dma_do(DMAOp &op);
  void dma_trigger();

 public:
  Runner(Device &dev_);

  /** Run the simulation */
  int runMain(int argc, char *argv[]);

  /* these three are for `Runner::Device`. */
  void issue_dma(DMAOp &op);
  void msi_issue(uint8_t vec);
  void msix_issue(uint8_t vec);
  void eth_send(const void *data, size_t len);

  void event_schedule(TimedEvent &evt);
  void event_cancel(TimedEvent &evt);

  uint64_t time_ps() const;
  uint64_t get_mac_addr() const;
};

/**
 * Very simple device that just has one register size.
 */
template <class TReg = uint32_t>
class SimpleDevice : public Runner::Device {
 public:
  virtual TReg reg_read(uint8_t bar, uint64_t addr) = 0;
  virtual void reg_write(uint8_t bar, uint64_t addr, TReg val) = 0;

  virtual void reg_read(uint8_t bar, uint64_t addr, void *dest, size_t len) {
    assert(len == sizeof(TReg));
    TReg r = reg_read(bar, addr);
    memcpy(dest, &r, sizeof(r));
  }

  virtual void reg_write(uint8_t bar, uint64_t addr, const void *src,
                         size_t len) {
    assert(len == sizeof(TReg));
    TReg r;
    memcpy(&r, src, sizeof(r));
    reg_write(bar, addr, r);
  }
};
}  // namespace nicbm

#endif  // SIMBRICKS_NICBM_NICBM_H_
