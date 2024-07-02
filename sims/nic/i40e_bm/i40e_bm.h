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

#pragma once

#include <stdint.h>

#include <deque>
#include <sstream>
#include <string>
extern "C" {
#include <simbricks/pcie/proto.h>
}
#include <simbricks/nicbm/nicbm.h>

// #define DEBUG_DEV
// #define DEBUG_ADMINQ
// #define DEBUG_LAN
// #define DEBUG_HMC
// #define DEBUG_QUEUES

struct i40e_aq_desc;
struct i40e_tx_desc;

namespace i40e {

class i40e_bm;
class lan;

class dma_base : public nicbm::DMAOp {
 public:
  /** i40e_bm will call this when dma is done */
  virtual void done() = 0;
};

class int_ev : public nicbm::TimedEvent {
 public:
  uint16_t vec;
  bool armed;

  int_ev();
};

class logger : public std::ostream {
 public:
  static const char endl = '\n';

 protected:
  std::string label;
  nicbm::Runner::Device &dev;
  nicbm::Runner *runner;
  std::stringstream ss;

 public:
  explicit logger(const std::string &label_, nicbm::Runner::Device &dev_);
  logger &operator<<(char c);
  logger &operator<<(int32_t c);
  logger &operator<<(uint8_t i);
  logger &operator<<(uint16_t i);
  logger &operator<<(uint32_t i);
  logger &operator<<(uint64_t i);
  logger &operator<<(bool c);
  logger &operator<<(const char *str);
  logger &operator<<(void *str);
};

/**
 * Base-class for descriptor queues (RX/TX, Admin RX/TX).
 *
 * Descriptor processing is split up into multiple phases:
 *
 *      - fetch: descriptor is read from host memory. This can be done in
 *        batches, while the batch sizes is limited by the minimum of
 *        MAX_ACTIVE_DESCS, max_active_capacity(), and max_fetch_capacity().
 *        Fetch is implemented by this base class.
 *
 *      - prepare: to be implemented in the sub class, but typically involves
 *        fetching buffer contents. Not guaranteed to happen in order. If
 *        overriden subclass must call desc_prepared() when done.
 *
 *      - process: to be implemented in the sub class. Guaranteed to be called
 *        in order. In case of tx, this actually sends the packet, in rx
 *        processing finishes when a packet for a descriptor has been received.
 *        subclass must call desc_processed() when done.
 *
 *      - write back: descriptor is written back to host-memory. Write-back
 *        capacity
 */
class queue_base {
 protected:
  static const uint32_t MAX_ACTIVE_DESCS = 128;

  class desc_ctx {
    friend class queue_base;

   public:
    enum state {
      DESC_EMPTY,
      DESC_FETCHING,
      DESC_PREPARING,
      DESC_PREPARED,
      DESC_PROCESSING,
      DESC_PROCESSED,
      DESC_WRITING_BACK,
      DESC_WRITTEN_BACK,
    };

   protected:
    queue_base &queue;

   public:
    enum state state;
    uint32_t index;
    void *desc;
    size_t desc_len;
    void *data;
    size_t data_len;
    size_t data_capacity;

    virtual void prepared();
    virtual void processed();

   protected:
    void data_fetch(uint64_t addr, size_t len);
    virtual void data_fetched(uint64_t addr, size_t len);
    void data_write(uint64_t addr, size_t len, const void *buf);
    virtual void data_written(uint64_t addr, size_t len);

   public:
    explicit desc_ctx(queue_base &queue_);
    virtual ~desc_ctx();

    virtual void prepare();
    virtual void process() = 0;
  };

  class dma_fetch : public dma_base {
   protected:
    queue_base &queue;

   public:
    uint32_t pos;
    dma_fetch(queue_base &queue_, size_t len);
    virtual ~dma_fetch();
    virtual void done();
  };

  class dma_wb : public dma_base {
   protected:
    queue_base &queue;

   public:
    uint32_t pos;
    dma_wb(queue_base &queue_, size_t len);
    virtual ~dma_wb();
    virtual void done();
  };

  class dma_data_fetch : public dma_base {
   protected:
    desc_ctx &ctx;

   public:
    size_t total_len;
    size_t part_offset;
    dma_data_fetch(desc_ctx &ctx_, size_t len, void *buffer);
    virtual ~dma_data_fetch();
    virtual void done();
  };

  class dma_data_wb : public dma_base {
   protected:
    desc_ctx &ctx;

   public:
    size_t total_len;
    size_t part_offset;
    dma_data_wb(desc_ctx &ctx_, size_t len);
    virtual ~dma_data_wb();
    virtual void done();
  };

 public:
  std::string qname;
  logger log;

 protected:
  i40e_bm &dev;
  desc_ctx *desc_ctxs[MAX_ACTIVE_DESCS];
  uint32_t active_first_pos;
  uint32_t active_first_idx;
  uint32_t active_cnt;

  uint64_t base;
  uint32_t len;
  uint32_t &reg_head;
  uint32_t &reg_tail;

  bool enabled;
  size_t desc_len;

  void ctxs_init();

  void trigger_fetch();
  void trigger_process();
  void trigger_writeback();
  void trigger();

  // returns how many descriptors the queue can fetch max during the next
  // fetch: default UINT32_MAX, but can be overriden by child classes
  virtual uint32_t max_fetch_capacity();
  virtual uint32_t max_writeback_capacity();
  virtual uint32_t max_active_capacity();

  virtual desc_ctx &desc_ctx_create() = 0;

  // dummy function, needs to be overriden if interrupts are required
  virtual void interrupt();

  // this does the actual write-back. Can be overridden
  virtual void do_writeback(uint32_t first_idx, uint32_t first_pos,
                            uint32_t cnt);

  // called by dma op when writeback has completed
  void writeback_done(uint32_t first_pos, uint32_t cnt);

 public:
  queue_base(const std::string &qname_, uint32_t &reg_head_,
             uint32_t &reg_tail_, i40e_bm &dev_);
  virtual void reset();
  void reg_updated();
  bool is_enabled();
};

class queue_admin_tx : public queue_base {
 protected:
  class admin_desc_ctx : public desc_ctx {
   protected:
    queue_admin_tx &aq;
    i40e_bm &dev;
    struct i40e_aq_desc *d;

    virtual void data_written(uint64_t addr, size_t len);

    // prepare completion descriptor (fills flags, and return value)
    void desc_compl_prepare(uint16_t retval, uint16_t extra_flags);
    // complete direct response
    void desc_complete(uint16_t retval, uint16_t extra_flags = 0);
    // complete indirect response
    void desc_complete_indir(uint16_t retval, const void *data, size_t len,
                             uint16_t extra_flags = 0,
                             bool ignore_datalen = false);

   public:
    admin_desc_ctx(queue_admin_tx &queue_, i40e_bm &dev);

    virtual void prepare();
    virtual void process();
  };

  uint64_t &reg_base;
  uint32_t &reg_len;

  virtual desc_ctx &desc_ctx_create();

 public:
  queue_admin_tx(i40e_bm &dev_, uint64_t &reg_base_, uint32_t &reg_len_,
                 uint32_t &reg_head_, uint32_t &reg_tail_);
  void reg_updated();
};

// host memory cache
class host_mem_cache {
 protected:
  static const uint16_t MAX_SEGMENTS = 0x1000;

  struct segment {
    uint64_t addr;
    uint16_t pgcount;
    bool valid;
    bool direct;
  };

  i40e_bm &dev;
  segment segs[MAX_SEGMENTS];

 public:
  class mem_op : public dma_base {
   public:
    bool failed;
  };

  explicit host_mem_cache(i40e_bm &dev);
  void reset();
  void reg_updated(uint64_t addr);

  // issue a hmc memory operation (address is in the context
  void issue_mem_op(mem_op &op);
};

class lan_queue_base : public queue_base {
 protected:
  class qctx_fetch : public host_mem_cache::mem_op {
   public:
    lan_queue_base &lq;

    explicit qctx_fetch(lan_queue_base &lq_);
    virtual void done();
  };

  lan &lanmgr;

  void ctx_fetched();
  void ctx_written_back();

  virtual void interrupt();
  virtual void initialize() = 0;

 public:
  bool enabling;
  size_t idx;
  uint32_t &reg_ena;
  uint32_t &fpm_basereg;
  uint32_t &reg_intqctl;
  size_t ctx_size;
  void *ctx;

  uint32_t reg_dummy_head;

  lan_queue_base(lan &lanmgr_, const std::string &qtype, uint32_t &reg_tail,
                 size_t idx_, uint32_t &reg_ena_, uint32_t &fpm_basereg,
                 uint32_t &reg_intqctl, uint16_t ctx_size);
  virtual void reset();
  void enable();
  void disable();
};

class lan_queue_tx : public lan_queue_base {
 protected:
  static const uint16_t MTU = 9024;

  class tx_desc_ctx : public desc_ctx {
   protected:
    lan_queue_tx &tq;

   public:
    i40e_tx_desc *d;

    explicit tx_desc_ctx(lan_queue_tx &queue_);

    virtual void prepare();
    virtual void process();
    virtual void processed();
  };

  class dma_hwb : public dma_base {
   protected:
    lan_queue_tx &queue;

   public:
    uint32_t pos;
    uint32_t cnt;
    uint32_t next_head;
    dma_hwb(lan_queue_tx &queue_, uint32_t pos, uint32_t cnt,
            uint32_t next_head);
    virtual ~dma_hwb();
    virtual void done();
  };

  uint8_t pktbuf[MTU];
  uint32_t tso_off;
  uint32_t tso_len;
  std::deque<tx_desc_ctx *> ready_segments;

  bool hwb;
  uint64_t hwb_addr;

  virtual void initialize();
  virtual desc_ctx &desc_ctx_create();

  virtual void do_writeback(uint32_t first_idx, uint32_t first_pos,
                            uint32_t cnt);
  bool trigger_tx_packet();
  void trigger_tx();

 public:
  lan_queue_tx(lan &lanmgr_, uint32_t &reg_tail, size_t idx, uint32_t &reg_ena,
               uint32_t &fpm_basereg, uint32_t &reg_intqctl);
  virtual void reset();
};

class lan_queue_rx : public lan_queue_base {
 protected:
  class rx_desc_ctx : public desc_ctx {
   protected:
    lan_queue_rx &rq;
    virtual void data_written(uint64_t addr, size_t len);

   public:
    explicit rx_desc_ctx(lan_queue_rx &queue_);
    virtual void process();
    void packet_received(const void *data, size_t len, bool last,
                         int rxtime_id);
  };

  uint16_t dbuff_size;
  uint16_t hbuff_size;
  uint16_t rxmax;
  bool crc_strip;

  std::deque<rx_desc_ctx *> dcache;

  virtual void initialize();
  virtual desc_ctx &desc_ctx_create();
  bool ptp_rx_sample(const void *data, size_t len);

 public:
  lan_queue_rx(lan &lanmgr_, uint32_t &reg_tail, size_t idx, uint32_t &reg_ena,
               uint32_t &fpm_basereg, uint32_t &reg_intqctl);
  virtual void reset();
  void packet_received(const void *data, size_t len, uint32_t hash);
};

class rss_key_cache {
 protected:
  static const size_t key_len = 52;
  // big enough for 2x ipv6 (2x128 + 2x16)
  static const size_t cache_len = 288;
  bool cache_dirty;
  const uint32_t (&key)[key_len / 4];
  uint32_t cache[cache_len];

  void build();

 public:
  explicit rss_key_cache(const uint32_t (&key_)[key_len / 4]);
  void set_dirty();
  uint32_t hash_ipv4(uint32_t sip, uint32_t dip, uint16_t sp, uint16_t dp);
};

// rx tx management
class lan {
 protected:
  friend class lan_queue_base;
  friend class lan_queue_tx;
  friend class lan_queue_rx;

  i40e_bm &dev;
  logger log;
  rss_key_cache rss_kc;
  const size_t num_qs;
  lan_queue_rx **rxqs;
  lan_queue_tx **txqs;

  bool rss_steering(const void *data, size_t len, uint16_t &queue,
                    uint32_t &hash);

 public:
  lan(i40e_bm &dev, size_t num_qs);
  void reset();
  void qena_updated(uint16_t idx, bool rx);
  void tail_updated(uint16_t idx, bool rx);
  void rss_key_updated();
  void packet_received(const void *data, size_t len);
};

class ptpmgr {
 protected:
  static const uint64_t CLOCK_HZ = 625000000;

  i40e_bm &dev;
  uint64_t last_updated;
  __uint128_t last_val;
  int64_t offset;
  uint64_t inc_val;
  bool adj_neg;
  uint32_t adj_val;

  uint64_t update_clock();

 public:
  explicit ptpmgr(i40e_bm &dev);
  uint64_t phc_read();
  void phc_write(uint64_t val);

  uint32_t adj_get();
  void adj_set(uint32_t val);

  void inc_set(uint64_t inc);
};

class shadow_ram {
 protected:
  i40e_bm &dev;
  logger log;

 public:
  explicit shadow_ram(i40e_bm &dev);
  void reg_updated();
  uint16_t read(uint16_t addr);
  void write(uint16_t addr, uint16_t val);
};

class i40e_bm : public nicbm::Runner::Device {
 protected:
  friend class queue_admin_tx;
  friend class host_mem_cache;
  friend class lan;
  friend class lan_queue_base;
  friend class lan_queue_rx;
  friend class lan_queue_tx;
  friend class shadow_ram;

  static const unsigned BAR_REGS = 0;
  static const unsigned BAR_IO = 2;
  static const unsigned BAR_MSIX = 3;

  static const uint32_t NUM_QUEUES = 1536;
  static const uint32_t NUM_PFINTS = 128;
  static const uint32_t NUM_VSIS = 384;
  static const uint16_t MAX_MTU = 2048;
  static const uint8_t NUM_ITR = 3;

  struct i40e_regs {
    uint32_t glgen_rstctl;
    uint32_t glgen_stat;
    uint32_t gllan_rctl_0;
    uint32_t pfint_lnklst0;
    uint32_t pfint_icr0_ena;
    uint32_t pfint_icr0;
    uint32_t pfint_itr0[NUM_ITR];
    uint32_t pfint_itrn[NUM_ITR][NUM_PFINTS];

    uint32_t pfint_stat_ctl0;
    uint32_t pfint_dyn_ctl0;
    uint32_t pfint_dyn_ctln[NUM_PFINTS - 1];
    uint32_t pfint_lnklstn[NUM_PFINTS - 1];
    uint32_t pfint_raten[NUM_PFINTS - 1];
    uint32_t gllan_txpre_qdis[12];

    uint32_t glnvm_srctl;
    uint32_t glnvm_srdata;

    uint32_t qint_tqctl[NUM_QUEUES];
    uint32_t qtx_ena[NUM_QUEUES];
    uint32_t qtx_tail[NUM_QUEUES];
    uint32_t qtx_ctl[NUM_QUEUES];
    uint32_t qint_rqctl[NUM_QUEUES];
    uint32_t qrx_ena[NUM_QUEUES];
    uint32_t qrx_tail[NUM_QUEUES];

    uint32_t glhmc_lantxbase[16];
    uint32_t glhmc_lantxcnt[16];
    uint32_t glhmc_lanrxbase[16];
    uint32_t glhmc_lanrxcnt[16];

    uint32_t pfhmc_sdcmd;
    uint32_t pfhmc_sddatalow;
    uint32_t pfhmc_sddatahigh;
    uint32_t pfhmc_pdinv;
    uint32_t pfhmc_errorinfo;
    uint32_t pfhmc_errordata;

    uint64_t pf_atqba;
    uint32_t pf_atqlen;
    uint32_t pf_atqh;
    uint32_t pf_atqt;

    uint64_t pf_arqba;
    uint32_t pf_arqlen;
    uint32_t pf_arqh;
    uint32_t pf_arqt;

    uint32_t pfqf_ctl_0;

    uint32_t pfqf_hkey[13];
    uint32_t pfqf_hlut[128];

    uint32_t prtdcb_fccfg;
    uint32_t prtdcb_mflcn;
    uint32_t prt_l2tagsen;
    uint32_t prtqf_ctl_0;

    uint32_t glrpb_ghw;
    uint32_t glrpb_glw;
    uint32_t glrpb_phw;
    uint32_t glrpb_plw;

    uint32_t prtsyn_ctl_0;
    uint32_t prtsyn_ctl_1;
    uint32_t prtsyn_aux_0;
    uint32_t prtsyn_stat_0;
    uint32_t prtsyn_stat_1;

    uint64_t prtsyn_inc;
    uint32_t prtsyn_inc_l;
    uint32_t prtsyn_inc_h;

    uint32_t prtsyn_time_l;
    uint32_t prtsyn_time_h;
    bool prtsyn_rxtime_lock[4];
    uint64_t prtsyn_rxtime[4];
    uint32_t prtsyn_rxtime_h[4];
    uint64_t prtsyn_txtime;
    uint32_t prtsyn_txtime_h;
  };

 public:
  i40e_bm();
  ~i40e_bm();

  void SetupIntro(struct SimbricksProtoPcieDevIntro &di) override;
  void RegRead(uint8_t bar, uint64_t addr, void *dest, size_t len) override;
  virtual uint32_t RegRead32(uint8_t bar, uint64_t addr);
  void RegWrite(uint8_t bar, uint64_t addr, const void *src,
                size_t len) override;
  virtual void RegWrite32(uint8_t bar, uint64_t addr, uint32_t val);
  void DmaComplete(nicbm::DMAOp &op) override;
  void EthRx(uint8_t port, const void *data, size_t len) override;
  void Timed(nicbm::TimedEvent &ev) override;

  virtual void SignalInterrupt(uint16_t vector, uint8_t itr);

 protected:
  logger log;
  i40e_regs regs;
  queue_admin_tx pf_atq;
  host_mem_cache hmc;
  shadow_ram shram;
  lan lanmgr;
  ptpmgr ptp;

  int_ev intevs[NUM_PFINTS];

  /** Read from the I/O bar */
  virtual uint32_t reg_io_read(uint64_t addr);
  /** Write to the I/O bar */
  virtual void reg_io_write(uint64_t addr, uint32_t val);

  /** 32-bit read from the memory bar (should be the default) */
  virtual uint32_t reg_mem_read32(uint64_t addr);
  /** 32-bit write to the memory bar (should be the default) */
  virtual void reg_mem_write32(uint64_t addr, uint32_t val);

  void reset(bool indicate_done);
};

// places the tcp checksum in the packet (assuming ipv4)
void xsum_tcp(void *tcphdr, size_t l4len);

// places the udpp checksum in the packet (assuming ipv4)
void xsum_udp(void *udpphdr, size_t l4len);

// calculates the full ipv4 & tcp checksum without assuming any pseudo header
// xsums
void xsum_tcpip_tso(void *iphdr, uint8_t iplen, uint8_t l4len, uint16_t paylen);

void tso_postupdate_header(void *iphdr, uint8_t iplen, uint8_t l4len,
                           uint16_t paylen);

}  // namespace i40e
