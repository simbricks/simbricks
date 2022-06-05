#include <iostream>
#include <stdarg.h>

#include <simbricks/nicbm/nicbm.h>
#include "sims/nic/e1000_gem5/i8254xGBe.h"

static nicbm::Runner *runner;
static bool debug_enable = false;

class Gem5DMAOp : public nicbm::DMAOp, public nicbm::TimedEvent {
  public:
    EventFunctionWrapper &ev_;
    Gem5DMAOp(EventFunctionWrapper &ev) : ev_(ev) {}
    virtual ~Gem5DMAOp() = default;
};


/******************************************************************************/
/* nicbm callbacks */

void IGbE::SetupIntro(struct SimbricksProtoPcieDevIntro &di)
{
  di.bars[0].len = 128 * 1024;
  di.bars[0].flags = SIMBRICKS_PROTO_PCIE_BAR_64;

  di.pci_vendor_id = 0x8086;
  di.pci_device_id = 0x1075;
  di.pci_class = 0x02;
  di.pci_subclass = 0x00;
  di.pci_revision = 0x00;
}

void IGbE::RegRead(uint8_t bar, uint64_t addr, void *dest,
             size_t len)
{
    read(addr, len, dest);
    // TODO delay!
}

void IGbE::RegWrite(uint8_t bar, uint64_t addr, const void *src,
              size_t len)
{
    write(addr, len, src);
    // TODO delay!
}

void IGbE::DmaComplete(nicbm::DMAOp &op)
{
    Gem5DMAOp *dma = dynamic_cast <Gem5DMAOp *>(&op);
    if (dma->write_) {
        delete[] ((uint8_t *) dma->data_);
    } else {
        // schedule callback event. THis is at the current time, but can't call
        // directly to ensure event priorities are respected.
        dma->ev_.sched = true;
        dma->ev_.time_ = runner_->TimePs();
        runner_->EventSchedule(dma->ev_);
    }
    delete dma;
}

void IGbE::EthRx(uint8_t port, const void *data, size_t len)
{
    EthPacketPtr pp = std::make_shared<EthPacketData>(len);
    pp->length = len;
    memcpy(pp->data, data, len);

    ethRxPkt(pp);
}

void IGbE::Timed(nicbm::TimedEvent &te)
{
    if (Gem5DMAOp *dma = dynamic_cast <Gem5DMAOp *>(&te)) {
        runner_->IssueDma(*dma);
    } else if (EventFunctionWrapper *evw =
            dynamic_cast <EventFunctionWrapper *>(&te)) {
        evw->sched = false;
        evw->callback();
    } else {
        abort();
    }
}


/******************************************************************************/
/* gem5-ish APIs */

Tick IGbE::clockEdge(Tick t)
{
    if (t % 1000 != 0)
        t += 1000 - (t % 1000);
    t += 1000;
    return t;
}

void IGbE::schedule(EventFunctionWrapper &ev, Tick t)
{
    if (ev.sched) {
        fprintf(stderr, "schedule: already scheduled\n");
        abort();
    }
    ev.time_ = t;
    ev.sched = true;
    runner_->EventSchedule(ev);
}

void IGbE::reschedule(EventFunctionWrapper &ev, Tick t, bool always)
{
    if (ev.sched) {
        runner_->EventCancel(ev);
        ev.sched = false;
    } else if (!always) {
        fprintf(stderr, "reschedule: not yet scheduled\n");
        abort();
    }
    schedule(ev, t);
}

void IGbE::deschedule(EventFunctionWrapper &ev)
{
    if (!ev.sched) {
        fprintf(stderr, "deschedule: not scheduledd\n");
        abort();
    }
    runner_->EventCancel(ev);
    ev.sched = false;
}

void IGbE::intrPost()
{
    runner_->IntXIssue(true);
}

void IGbE::intrClear()
{
    runner_->IntXIssue(false);
}

void IGbE::dmaWrite(Addr daddr, size_t len, EventFunctionWrapper &ev,
    const void *buf, Tick delay)
{
    Gem5DMAOp *op = new Gem5DMAOp(ev);
    op->data_ = new uint8_t[len];
    memcpy(op->data_, buf, len);
    op->len_ = len;
    op->write_ = true;
    op->dma_addr_ = daddr;
    op->priority_ = 1;
    op->time_ = runner_->TimePs() + delay;
    runner_->EventSchedule(*op);

    ev.time_ = runner_->TimePs() + delay;
    runner_->EventSchedule(ev);
}

void IGbE::dmaRead(Addr saddr, size_t len, EventFunctionWrapper &ev,
    void *buf, Tick delay)
{
    ev.sched = true;

    Gem5DMAOp *op = new Gem5DMAOp(ev);
    op->data_ = buf;
    op->len_ = len;
    op->write_ = false;
    op->dma_addr_ = saddr;
    op->time_ = runner_->TimePs() + delay;
    op->priority_ = 2;
    runner_->EventSchedule(*op);

}

bool IGbE::sendPacket(EthPacketPtr p)
{
    runner_->EthSend(p->data, p->length);
    ethTxDone();
    return true;
}

void warn(const char *fmt, ...)
{
    fprintf(stderr, "warn: ");
    va_list va;
    va_start(va, fmt);
    vfprintf(stderr, fmt, va);
    va_end(va);
}

void panic(const char *fmt, ...)
{
    fprintf(stderr, "panic: ");
    va_list va;
    va_start(va, fmt);
    vfprintf(stderr, fmt, va);
    va_end(va);

    abort();
}

static void debug_init()
{
#ifdef DEBUG_E1000
    char *debug_env = getenv("E1000_DEBUG");
    if (debug_env &&
        (!strcmp(debug_env, "1") ||
         !strcmp(debug_env, "y") ||
         !strcmp(debug_env, "Y")))
    {
        warn("enabling debug messages because E1000_DEBUG envar set\n");
        debug_enable = true;
    }
#endif
}

void debug_printf(const char *fmt, ...)
{
    if (debug_enable) {
        va_list val;
        va_start(val, fmt);
        fprintf(stderr, "%lu: ", runner->TimePs());
        vfprintf(stderr, fmt, val);
        va_end(val);
    }
}

/******************************************************************************/

int main(int argc, char *argv[])
{
    debug_init();

    IGbEParams params;
    params.rx_fifo_size = 384 * 1024;
    params.tx_fifo_size = 384 * 1024;
    params.fetch_delay = 10 * 1000;
    params.wb_delay = 10 * 1000;
    params.fetch_comp_delay = 10 * 1000;
    params.wb_comp_delay = 10 * 1000;
    params.rx_write_delay = 0;
    params.tx_read_delay = 0;
    params.pio_delay = 0; // TODO
    params.rx_desc_cache_size = 64;
    params.tx_desc_cache_size = 64;
    params.phy_pid = 0x02A8;
    params.phy_epid = 0x0380;

    IGbE *dev = new IGbE(&params);

    runner = new nicbm::Runner(*dev);
    if (runner->ParseArgs(argc, argv))
        return EXIT_FAILURE;

    dev->init();
    return runner->RunMain();
}