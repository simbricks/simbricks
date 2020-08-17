namespace nicbm {

#include <cassert>

extern "C" {
    #include <nicsim.h>
}

static const size_t MAX_DMA_LEN = 2048;

struct DMAOp {
    bool write;
    uint64_t dma_addr;
    size_t len;
    void *data;
};


class Runner {
    public:
        class Device {
            public:
                /**
                 * Initialize device specific parameters (pci dev/vendor id,
                 * BARs etc. in intro struct.
                 */
                virtual void setup_intro(struct cosim_pcie_proto_dev_intro &di)
                    = 0;

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
                virtual void reg_write(uint8_t bar, uint64_t addr,
                        const void *src, size_t len) = 0;

                /**
                 * the previously issued DMA operation `op` completed.
                 */
                virtual void dma_complete(DMAOp &op) = 0;

                /**
                 * A packet has arrived on the wire, of length `len` with
                 * payload `data`.
                 */
                virtual void eth_rx(uint8_t port, const void *data, size_t len)
                    = 0;
        };

    protected:
        Device &dev;
        struct nicsim_params nsparams;

        volatile union cosim_pcie_proto_d2h *d2h_alloc(void);
        volatile union cosim_eth_proto_d2n *d2n_alloc(void);

        void h2d_read(volatile struct cosim_pcie_proto_h2d_read *read);
        void h2d_write(volatile struct cosim_pcie_proto_h2d_write *write);
        void h2d_readcomp(volatile struct cosim_pcie_proto_h2d_readcomp *rc);
        void h2d_writecomp(volatile struct cosim_pcie_proto_h2d_writecomp *wc);
        void poll_h2d();

        void eth_recv(volatile struct cosim_eth_proto_n2d_recv *recv);
        void poll_n2d();

    public:
        Runner(Device &dev_);

        /** */
        int runMain(int argc, char *argv[]);

        /* these three are for `Runner::Device`. */
        void issue_dma(DMAOp &op);
        void msi_issue(uint8_t vec);
        void eth_send(const void *data, size_t len);
};

/* Very simple device that just has one register size */
template <class TReg = uint32_t>
class SimpleDevice : public Runner::Device {
    public:
        virtual TReg reg_read(uint8_t bar, uint64_t addr) = 0;
        virtual void reg_write(uint8_t bar, uint64_t addr, TReg val) = 0;

        virtual void reg_read(uint8_t bar, uint64_t addr, void *dest,
                size_t len)
        {
            assert(len == sizeof(TReg));
            TReg r = reg_read(bar, addr);
            memcpy(dest, &r, sizeof(r));
        }

        virtual void reg_write(uint8_t bar, uint64_t addr,
                const void *src, size_t len)
        {
            assert(len == sizeof(TReg));
            TReg r;
            memcpy(&r, src, sizeof(r));
            reg_write(bar, addr, r);
        }
};
}
