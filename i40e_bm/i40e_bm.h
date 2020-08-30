#pragma once

#include <list>
#include <vector>
#include <stdint.h>
extern "C" {
#include <cosim_pcie_proto.h>
}
#include <nicbm.h>

struct i40e_aq_desc;

namespace i40e {

class i40e_bm;

class dma_base : public nicbm::DMAOp {
    public:
        /** i40e_bm will call this when dma is done */
        virtual void done() = 0;
};

class queue_base {
    protected:
        class dma_fetch : public dma_base {
            protected:
                queue_base &queue;
            public:
                uint32_t index;
                dma_fetch(queue_base &queue_, size_t len);
                virtual ~dma_fetch();
                virtual void done();
        };

        class dma_data_fetch : public dma_base {
            protected:
                queue_base &queue;
            public:
                uint32_t index;
                void *desc;
                dma_data_fetch(queue_base &queue_, size_t len, const void *desc,
                        size_t desc_len);
                virtual ~dma_data_fetch();
                virtual void done();
        };

        class dma_wb : public dma_base {
            protected:
                queue_base &queue;
            public:
                uint32_t index;
                dma_wb(queue_base &queue_, size_t len);
                virtual ~dma_wb();
                virtual void done();
        };

        class dma_data_wb : public dma_base {
            protected:
                queue_base &queue;
                dma_wb &desc_dma;
            public:
                uint32_t index;
                dma_data_wb(queue_base &queue_, size_t len, dma_wb &desc_dma_);
                virtual ~dma_data_wb();
                virtual void done();
        };

        uint64_t base;
        uint32_t len;
        uint32_t fetch_head;
        uint32_t &reg_head;
        uint32_t &reg_tail;

        bool enabled;
        size_t desc_len;

        void trigger_fetch();
        void data_fetch(const void *desc, uint32_t idx, uint64_t addr, size_t len);
        void desc_writeback(const void *desc, uint32_t idx);
        void desc_writeback_indirect(const void *desc, uint32_t idx,
                uint64_t data_addr, const void *data, size_t data_len);

        // called when a descriptor is fetched
        virtual void desc_fetched(void *desc, uint32_t idx) = 0;
        // called when data is fetched
        virtual void data_fetched(void *desc, uint32_t idx, void *data) = 0;
        virtual void desc_written_back(uint32_t idx);

    public:
        queue_base(uint32_t &reg_head_, uint32_t &reg_tail_);
        void reg_updated();

};

class queue_admin_tx : public queue_base {
    protected:
        i40e_bm &dev;

        // prepare completion descriptor (fills flags, and return value)
        void desc_compl_prepare(struct i40e_aq_desc *d, uint16_t retval,
                uint16_t extra_flags);

        // complete direct response
        void desc_complete(struct i40e_aq_desc *d, uint32_t idx,
                uint16_t retval, uint16_t extra_flags = 0);
        // complete indirect response
        void desc_complete_indir(struct i40e_aq_desc *d, uint32_t idx,
                uint16_t retval, const void *data, size_t len,
                uint16_t extra_flags = 0);

        // run command
        virtual void cmd_run(void *desc, uint32_t idx, void *data);

        // called by base class when a descriptor has been fetched
        virtual void desc_fetched(void *desc, uint32_t idx);
        // called by basee class when data for a descriptor has been fetched
        virtual void data_fetched(void *desc, uint32_t idx, void *data);

        uint64_t &reg_base;
        uint32_t &reg_len;
    public:
        queue_admin_tx(i40e_bm &dev_, uint64_t &reg_base_,
                uint32_t &reg_len_, uint32_t &reg_head_, uint32_t &reg_tail_);
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

        host_mem_cache(i40e_bm &dev);
        void reg_updated(uint64_t addr);

        // issue a hmc memory operation (address is in the context
        void issue_mem_op(mem_op &op);
};


class shadow_ram {
    protected:
        i40e_bm &dev;

    public:
        shadow_ram(i40e_bm &dev);
        void reg_updated();
        uint16_t read(uint16_t addr);
        void write(uint16_t addr, uint16_t val);
};

class i40e_bm : public nicbm::Runner::Device {
protected:
    friend class shadow_ram;
    friend class queue_admin_tx;

    static const unsigned BAR_REGS = 0;
    static const unsigned BAR_IO = 2;

    static const uint32_t NUM_QUEUES = 1536;
    static const uint32_t NUM_PFINTS = 512;
    static const uint16_t MAX_MTU = 2048;

    struct i40e_regs {
        uint32_t glgen_rstctl;
        uint32_t gllan_rctl_0;
        uint32_t pfint_lnklst0;
        uint32_t pfint_icr0_ena;

        uint32_t pfint_dyn_ctln[NUM_PFINTS - 1];
        uint32_t pfint_lnklstn[NUM_PFINTS - 1];
        uint32_t pfint_raten[NUM_PFINTS - 1];
        uint32_t gllan_txpre_qdis[12];

        uint32_t glnvm_srctl;
        uint32_t glnvm_srdata;

        uint32_t qint_tqctl[NUM_QUEUES];
        uint32_t qtx_ena[NUM_QUEUES];
        uint32_t qint_rqctl[NUM_QUEUES];
        uint32_t qrx_ena[NUM_QUEUES];

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

        uint32_t glqf_hkey[13];
    };

public:
    nicbm::Runner *runner;

    i40e_bm();
    ~i40e_bm();

    virtual void setup_intro(struct cosim_pcie_proto_dev_intro &di);
    virtual void reg_read(uint8_t bar, uint64_t addr, void *dest, size_t len);
    virtual void reg_write(uint8_t bar, uint64_t addr, const void *src,
            size_t len);
    virtual void dma_complete(nicbm::DMAOp &op);
    virtual void eth_rx(uint8_t port, const void *data, size_t len);

protected:
    i40e_regs regs;
    queue_admin_tx pf_atq;
    host_mem_cache hmc;
    shadow_ram shram;

    /** Read from the I/O bar */
    virtual uint32_t reg_io_read(uint64_t addr);
    /** Write to the I/O bar */
    virtual void reg_io_write(uint64_t addr, uint32_t val);

    /** 32-bit read from the memory bar (should be the default) */
    virtual uint32_t reg_mem_read32(uint64_t addr);
    /** 32-bit write to the memory bar (should be the default) */
    virtual void reg_mem_write32(uint64_t addr, uint32_t val);

    void reset();
};

} // namespace corundum
