#include <set>
#include <deque>

namespace nicbm {

#include <cassert>

extern "C" {
    #include <nicsim.h>
}

static const size_t MAX_DMA_LEN = 2048;

class DMAOp {
    public:
        virtual ~DMAOp() { }
        bool write;
        uint64_t dma_addr;
        size_t len;
        void *data;
};

class TimedEvent {
    public:
        virtual ~TimedEvent() { }
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

                /**
                 * A timed event is due.
                 */
                virtual void timed_event(TimedEvent &ev);
        };

    protected:
        struct event_cmp {
            bool operator() (TimedEvent *a, TimedEvent *b)
            {
                return a->time < b->time;
            }
        };

        Device &dev;
        std::set<TimedEvent *, event_cmp> events;
        std::deque<DMAOp *> dma_queue;
        size_t dma_pending;
        uint64_t mac_addr;
        struct nicsim_params nsparams;
        struct cosim_pcie_proto_dev_intro dintro;

        volatile union cosim_pcie_proto_d2h *d2h_alloc(void);
        volatile union cosim_eth_proto_d2n *d2n_alloc(void);

        void h2d_read(volatile struct cosim_pcie_proto_h2d_read *read);
        void h2d_write(volatile struct cosim_pcie_proto_h2d_write *write);
        void h2d_readcomp(volatile struct cosim_pcie_proto_h2d_readcomp *rc);
        void h2d_writecomp(volatile struct cosim_pcie_proto_h2d_writecomp *wc);
        void poll_h2d();

        void eth_recv(volatile struct cosim_eth_proto_n2d_recv *recv);
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
