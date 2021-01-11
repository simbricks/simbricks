#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <signal.h>
#include <cassert>

#include "corundum_bm.h"

static nicbm::Runner *runner;

namespace corundum {

DescRing::DescRing()
    : _dmaAddr(0), _sizeLog(0), _size(0), _sizeMask(0),
    _index(0), _headPtr(0), _tailPtr(0),
    _currHead(0), _currTail(0), active(false), armed(false)
{
}

DescRing::~DescRing()
{
}


addr_t
DescRing::dmaAddr()
{
    return this->_dmaAddr;
}

size_t
DescRing::sizeLog()
{
    return this->_sizeLog;
}

unsigned
DescRing::index()
{
    return this->_index;
}

ptr_t
DescRing::headPtr()
{
    return this->_headPtr;
}

ptr_t
DescRing::tailPtr()
{
    return this->_tailPtr;
}

void
DescRing::setDMALower(uint32_t addr)
{
    this->_dmaAddr &= 0xFFFFFFFF00000000;
    this->_dmaAddr |= (addr_t)addr;
}

void
DescRing::setDMAUpper(uint32_t addr)
{
    this->_dmaAddr &= 0xFFFFFFFF;
    this->_dmaAddr |= ((addr_t)addr << 32);
}

void
DescRing::setSizeLog(size_t size_log)
{
    if (size_log & QUEUE_ACTIVE_MASK) {
        this->active = true;
    } else {
        this->active = false;
    }

    this->_sizeLog = size_log & 0xFF;
    this->_size = 1 << this->_sizeLog;
    this->_sizeMask = this->_size - 1;
    this->cplDma.resize(this->_size, false);
}

void
DescRing::setIndex(unsigned index)
{
    assert(!(index & QUEUE_CONT_MASK));
    if (index & QUEUE_ARM_MASK) {
        this->armed = true;
    }
    this->_index = index & 0xFF;
}

void
DescRing::setHeadPtr(ptr_t ptr)
{
    this->_headPtr = ptr;
}

void
DescRing::setTailPtr(ptr_t ptr)
{
    this->_tailPtr = ptr;
}

bool
DescRing::empty()
{
    return (this->_headPtr == this->_currTail);
}

bool
DescRing::full()
{
    return (this->_currHead - this->_tailPtr >= this->_size);
}


bool
DescRing::updatePtr(ptr_t ptr, bool head)
{
    ptr_t curr_ptr = head ? this->_headPtr : this->_tailPtr;
    if (ptr != curr_ptr) {
        // out of order completion
        this->cplDma[ptr & this->_sizeMask] = true;
        return false;
    }
    /* Safe to update the pointer. Also check if any DMA is completed
     * out-of-order in front of us.
     */
    curr_ptr = ptr & this->_sizeMask;

    do {
        if (head) {
            this->_headPtr++;
        } else {
            this->_tailPtr++;
        }
        this->cplDma[curr_ptr] = false;
        curr_ptr = (curr_ptr + 1) & this->_sizeMask;
    } while (this->cplDma.at(curr_ptr));
    return true;
}

EventRing::EventRing()
{
}

EventRing::~EventRing()
{
}

void
EventRing::dmaDone(DMAOp *op)
{
    assert(op->write);
    switch (op->type) {
    case DMA_TYPE_EVENT:
        if (updatePtr((ptr_t)op->tag, true)) {
            runner->msi_issue(0);
        }
        delete op;
        break;
    default:
        fprintf(stderr, "Unknown DMA type %u\n", op->type);
        abort();
    }
}

void
EventRing::issueEvent(unsigned type, unsigned source)
{
    assert(type == EVENT_TYPE_TX_CPL || type == EVENT_TYPE_RX_CPL);
    if (this->armed) {
        if (full()) {
            fprintf(stderr, "Event ring is rull\n");
            return;
        }
        addr_t dma_addr = this->_dmaAddr + (this->_currHead & this->_sizeMask) * EVENT_SIZE;
        /* Issue DMA write */
        DMAOp *op = new DMAOp;
        op->type = DMA_TYPE_EVENT;
        op->dma_addr = dma_addr;
        op->len = EVENT_SIZE;
        op->ring = this;
        op->tag = this->_currHead;
        op->write = true;
        Event *event = (Event *)op->data;
        memset(event, 0, sizeof(Event));
        event->type = type;
        event->source = source;
        runner->issue_dma(*op);
        this->_currHead++;
        this->armed = false;
    }
}

CplRing::CplRing(EventRing *eventRing)
    : eventRing(eventRing)
{
}

CplRing::~CplRing()
{
}

void
CplRing::dmaDone(DMAOp *op)
{
    assert(op->write);
    switch (op->type) {
    case DMA_TYPE_TX_CPL:
    case DMA_TYPE_RX_CPL: {
        if (updatePtr((ptr_t)op->tag, true)) {
            unsigned type = op->type == DMA_TYPE_TX_CPL ? EVENT_TYPE_TX_CPL :
                EVENT_TYPE_RX_CPL;
            this->eventRing->issueEvent(type, 0);
        }
        delete op;
        break;
    }
    default:
        fprintf(stderr, "Unknown DMA type %u\n", op->type);
        abort();
    }
}

void
CplRing::complete(unsigned index, size_t len, bool tx)
{
    CplData data;
    data.index = index;
    data.len = len;
    data.tx = tx;
    this->pending.push_back(data);
    while (!full() && !this->pending.empty()) {
        CplData &data = this->pending.front();
        addr_t dma_addr = this->_dmaAddr + (this->_currHead & this->_sizeMask) * CPL_SIZE;
        /* Issue DMA write */
        DMAOp *op = new DMAOp;
        op->type = data.tx ? DMA_TYPE_TX_CPL : DMA_TYPE_RX_CPL;
        op->dma_addr = dma_addr;
        op->len = CPL_SIZE;
        op->ring = this;
        op->tag = this->_currHead;
        op->write = true;
        Cpl *cpl = (Cpl *)op->data;
        memset(cpl, 0, sizeof(Cpl));
        cpl->index = data.index;
        cpl->len = data.len;
        this->pending.pop_front();
        runner->issue_dma(*op);
        this->_currHead++;
    }
}

TxRing::TxRing(CplRing *cplRing)
    : txCplRing(cplRing)
{
}

TxRing::~TxRing()
{
}

void
TxRing::setHeadPtr(ptr_t ptr)
{
    DescRing::setHeadPtr(ptr);
    while (this->_currTail != this->_headPtr) {
        unsigned index = this->_currTail & this->_sizeMask;
        addr_t dma_addr = this->_dmaAddr + index * DESC_SIZE;
        /* Issue DMA read */
        DMAOp *op = new DMAOp;
        op->type = DMA_TYPE_DESC;
        op->dma_addr = dma_addr;
        op->len = DESC_SIZE;
        op->ring = this;
        op->tag = this->_currTail;
        op->write = false;
        runner->issue_dma(*op);
        this->_currTail++;
    }
}

void
TxRing::dmaDone(DMAOp *op)
{
    switch (op->type) {
    case DMA_TYPE_DESC: {
        assert(!op->write);
        Desc *desc = (Desc *)op->data;
        op->type = DMA_TYPE_MEM;
        op->dma_addr = desc->addr;
        op->len = desc->len;
        op->write = false;
        runner->issue_dma(*op);
        break;
    }
    case DMA_TYPE_MEM:
        assert(!op->write);
        runner->eth_send(op->data, op->len);
        updatePtr((ptr_t)op->tag, false);
        this->txCplRing->complete(op->tag, op->len, true);
        delete op;
        break;
    default:
        fprintf(stderr, "Unknown DMA type %u\n", op->type);
        abort();
    }
}

RxRing::RxRing(CplRing *cplRing)
    : rxCplRing(cplRing)
{
}

RxRing::~RxRing()
{
}

void
RxRing::dmaDone(DMAOp *op)
{
    switch (op->type) {
    case DMA_TYPE_DESC: {
        assert(!op->write);
        Desc *desc = (Desc *)op->data;
        op->type = DMA_TYPE_MEM;
        op->dma_addr = desc->addr;
        op->len = op->rx_data->len;
        memcpy((void *)op->data, (void *)op->rx_data->data, op->len);
        delete op->rx_data;
        op->write = true;
        runner->issue_dma(*op);
        break;
    }
    case DMA_TYPE_MEM:
        assert(op->write);
        updatePtr((ptr_t)op->tag, false);
        this->rxCplRing->complete(op->tag, op->len, false);
        delete op;
        break;
    default:
        fprintf(stderr, "Unknown DMA type %u\n", op->type);
        abort();
    }
}

void
RxRing::rx(RxData *rx_data)
{
    if (empty()) {
        delete rx_data;
        return;
    }
    addr_t dma_addr = this->_dmaAddr + (this->_currTail & this->_sizeMask) * DESC_SIZE;
    /* Issue DMA read */
    DMAOp *op = new DMAOp;
    op->type = DMA_TYPE_DESC;
    op->dma_addr = dma_addr;
    op->len = DESC_SIZE;
    op->ring = this;
    op->rx_data = rx_data;
    op->tag = this->_currTail;
    op->write = false;
    runner->issue_dma(*op);
    this->_currTail++;
}

Port::Port()
    : _id(0), _features(0), _mtu(0),
    _schedCount(0), _schedOffset(0), _schedStride(0),
    _schedType(0), _rssMask(0), _schedEnable(false),
    _queueEnable(false)
{
}

Port::~Port()
{
}

unsigned
Port::id()
{
    return this->_id;
}

unsigned
Port::features()
{
    return this->_features;
}

size_t
Port::mtu()
{
    return this->_mtu;
}

size_t
Port::schedCount()
{
    return this->_schedCount;
}

addr_t
Port::schedOffset()
{
    return this->_schedOffset;
}

addr_t
Port::schedStride()
{
    return this->_schedStride;
}

unsigned
Port::schedType()
{
    return this->_schedType;
}


unsigned
Port::rssMask()
{
    return this->_rssMask;
}

void
Port::setId(unsigned id)
{
    this->_id = id;
}

void
Port::setFeatures(unsigned features)
{
    this->_features = features & (IF_FEATURE_RSS     |
                                  IF_FEATURE_PTP_TS  |
                                  IF_FEATURE_TX_CSUM |
                                  IF_FEATURE_RX_CSUM |
                                  IF_FEATURE_RX_HASH);
}

void
Port::setMtu(size_t mtu)
{
    this->_mtu = mtu;
}

void
Port::setSchedCount(size_t count)
{
    this->_schedCount = count;
}

void
Port::setSchedOffset(addr_t offset)
{
    this->_schedOffset = offset;
}

void
Port::setSchedStride(addr_t stride)
{
    this->_schedStride = stride;
}

void
Port::setSchedType(unsigned type)
{
    this->_schedType = type;
}

void
Port::setRssMask(unsigned mask)
{
    this->_rssMask = mask;
}

void
Port::schedEnable()
{
    this->_schedEnable = true;
}

void
Port::schedDisable()
{
    this->_schedEnable = false;
}

void
Port::queueEnable()
{
    this->_queueEnable = true;
}

void
Port::queueDisable()
{
    this->_queueEnable = false;
}

Corundum::Corundum()
    : txCplRing(&this->eventRing), rxCplRing(&this->eventRing),
    txRing(&this->txCplRing), rxRing(&this->rxCplRing), features(0)
{
    this->port.setId(0);
    this->port.setFeatures(this->features);
    this->port.setMtu(2048);
    this->port.setSchedCount(1);
    this->port.setSchedOffset(0x100000);
    this->port.setSchedStride(0x100000);
    this->port.setSchedType(0);
    this->port.setRssMask(0);
    this->port.schedDisable();
}

Corundum::~Corundum()
{
}

reg_t
Corundum::reg_read(uint8_t bar, addr_t addr)
{
    switch (addr) {
        case REG_FW_ID:
            return 32;
        case REG_FW_VER:
            return 1;
        case REG_BOARD_ID:
            return 0x43215678;
        case REG_BOARD_VER:
            return 1;
        case REG_PHC_COUNT:
            return 1;
        case REG_PHC_OFFSET:
            return 0x200;
        case REG_PHC_STRIDE:
            return 0x80;
        case REG_IF_COUNT:
            return 1;
        case REG_IF_STRIDE:
            return 0x80000;
        case REG_IF_CSR_OFFSET:
            return 0x80000;
        case PHC_REG_FEATURES:
            return 0x1;
        case PHC_REG_PTP_CUR_SEC_L:
            return 0x0;
        case PHC_REG_PTP_CUR_SEC_H:
            return 0x0;
        case IF_REG_IF_ID:
            return 0;
        case IF_REG_IF_FEATURES:
            return this->features;
        case IF_REG_EVENT_QUEUE_COUNT:
            return 1;
        case IF_REG_EVENT_QUEUE_OFFSET:
            return 0x100000;
        case IF_REG_TX_QUEUE_COUNT:
            return 1;
        case IF_REG_TX_QUEUE_OFFSET:
            return 0x200000;
        case IF_REG_TX_CPL_QUEUE_COUNT:
            return 1;
        case IF_REG_TX_CPL_QUEUE_OFFSET:
            return 0x400000;
        case IF_REG_RX_QUEUE_COUNT:
            return 1;
        case IF_REG_RX_QUEUE_OFFSET:
            return 0x600000;
        case IF_REG_RX_CPL_QUEUE_COUNT:
            return 1;
        case IF_REG_RX_CPL_QUEUE_OFFSET:
            return 0x700000;
        case IF_REG_PORT_COUNT:
            return 1;
        case IF_REG_PORT_OFFSET:
            return 0x800000;
        case IF_REG_PORT_STRIDE:
            return 0x200000;
        case EVENT_QUEUE_HEAD_PTR_REG:
            return this->eventRing.headPtr();
        case TX_QUEUE_ACTIVE_LOG_SIZE_REG:
            return this->txRing.sizeLog();
        case TX_QUEUE_TAIL_PTR_REG:
            return this->txRing.tailPtr();
        case TX_CPL_QUEUE_HEAD_PTR_REG:
            return this->txCplRing.headPtr();
        case RX_QUEUE_TAIL_PTR_REG:
            return this->rxRing.tailPtr();
        case RX_CPL_QUEUE_HEAD_PTR_REG:
            return this->rxCplRing.headPtr();
        case PORT_REG_PORT_ID:
            return this->port.id();
        case PORT_REG_PORT_FEATURES:
            return this->port.features();
        case PORT_REG_PORT_MTU:
            return this->port.mtu();
        case PORT_REG_SCHED_COUNT:
            return this->port.schedCount();
        case PORT_REG_SCHED_OFFSET:
            return this->port.schedOffset();
        case PORT_REG_SCHED_STRIDE:
            return this->port.schedStride();
        case PORT_REG_SCHED_TYPE:
            return this->port.schedType();
        default:
            fprintf(stderr, "Unknown register read %lx\n", addr);
            abort();
    }
}

void
Corundum::reg_write(uint8_t bar, uint64_t addr, reg_t val)
{
    switch (addr) {
        case REG_FW_ID:
        case REG_FW_VER:
        case REG_BOARD_ID:
        case REG_BOARD_VER:
        case REG_PHC_COUNT:
        case REG_PHC_OFFSET:
        case REG_PHC_STRIDE:
        case REG_IF_COUNT:
        case REG_IF_STRIDE:
        case REG_IF_CSR_OFFSET:
        case PHC_REG_FEATURES:
        case PHC_REG_PTP_SET_FNS:
        case PHC_REG_PTP_SET_NS:
        case PHC_REG_PTP_SET_SEC_L:
        case PHC_REG_PTP_SET_SEC_H:
            break;
        case EVENT_QUEUE_BASE_ADDR_REG:
            this->eventRing.setDMALower(val);
            break;
        case EVENT_QUEUE_BASE_ADDR_REG + 4:
            this->eventRing.setDMAUpper(val);
            break;
        case EVENT_QUEUE_ACTIVE_LOG_SIZE_REG:
            this->eventRing.setSizeLog(val);
            break;
        case EVENT_QUEUE_INTERRUPT_INDEX_REG:
            this->eventRing.setIndex(val);
            break;
        case EVENT_QUEUE_HEAD_PTR_REG:
            this->eventRing.setHeadPtr(val);
            break;
        case EVENT_QUEUE_TAIL_PTR_REG:
            this->eventRing.setTailPtr(val);
            break;
        case TX_QUEUE_BASE_ADDR_REG:
            this->txRing.setDMALower(val);
            break;
        case TX_QUEUE_BASE_ADDR_REG + 4:
            this->txRing.setDMAUpper(val);
            break;
        case TX_QUEUE_ACTIVE_LOG_SIZE_REG:
            this->txRing.setSizeLog(val);
            break;
        case TX_QUEUE_CPL_QUEUE_INDEX_REG:
            this->txRing.setIndex(val);
            break;
        case TX_QUEUE_HEAD_PTR_REG:
            this->txRing.setHeadPtr(val);
            break;
        case TX_QUEUE_TAIL_PTR_REG:
            this->txRing.setTailPtr(val);
            break;
        case TX_CPL_QUEUE_BASE_ADDR_REG:
            this->txCplRing.setDMALower(val);
            break;
        case TX_CPL_QUEUE_BASE_ADDR_REG + 4:
            this->txCplRing.setDMAUpper(val);
            break;
        case TX_CPL_QUEUE_ACTIVE_LOG_SIZE_REG:
            this->txCplRing.setSizeLog(val);
            break;
        case TX_CPL_QUEUE_INTERRUPT_INDEX_REG:
            this->txCplRing.setIndex(val);
            break;
        case TX_CPL_QUEUE_HEAD_PTR_REG:
            this->txCplRing.setHeadPtr(val);
            break;
        case TX_CPL_QUEUE_TAIL_PTR_REG:
            this->txCplRing.setTailPtr(val);
            break;
        case RX_QUEUE_BASE_ADDR_REG:
            this->rxRing.setDMALower(val);
            break;
        case RX_QUEUE_BASE_ADDR_REG + 4:
            this->rxRing.setDMAUpper(val);
            break;
        case RX_QUEUE_ACTIVE_LOG_SIZE_REG:
            this->rxRing.setSizeLog(val);
            break;
        case RX_QUEUE_CPL_QUEUE_INDEX_REG:
            this->rxRing.setIndex(val);
            break;
        case RX_QUEUE_HEAD_PTR_REG:
            this->rxRing.setHeadPtr(val);
            break;
        case RX_QUEUE_TAIL_PTR_REG:
            this->rxRing.setTailPtr(val);
            break;
        case RX_CPL_QUEUE_BASE_ADDR_REG:
            this->rxCplRing.setDMALower(val);
            break;
        case RX_CPL_QUEUE_BASE_ADDR_REG + 4:
            this->rxCplRing.setDMAUpper(val);
            break;
        case RX_CPL_QUEUE_ACTIVE_LOG_SIZE_REG:
            this->rxCplRing.setSizeLog(val);
            break;
        case RX_CPL_QUEUE_INTERRUPT_INDEX_REG:
            this->rxCplRing.setIndex(val);
            break;
        case RX_CPL_QUEUE_HEAD_PTR_REG:
            this->rxCplRing.setHeadPtr(val);
            break;
        case RX_CPL_QUEUE_TAIL_PTR_REG:
            this->rxCplRing.setTailPtr(val);
            break;
        case PORT_REG_SCHED_ENABLE:
            if (val) {
                this->port.schedEnable();
            } else {
                this->port.schedDisable();
            }
            break;
        case PORT_REG_RSS_MASK:
            this->port.setRssMask(val);
            break;
        case PORT_QUEUE_ENABLE:
            if (val) {
                this->port.queueEnable();
            } else {
                this->port.queueDisable();
            }
            break;
        default:
            fprintf(stderr, "Unknown register write %lx\n", addr);
            abort();
    }
}

void
Corundum::setup_intro(struct cosim_pcie_proto_dev_intro &di)
{
    di.bars[0].len = 1 << 24;
    di.bars[0].flags = COSIM_PCIE_PROTO_BAR_64;
    di.pci_vendor_id = 0x5543;
    di.pci_device_id = 0x1001;
    di.pci_class = 0x02;
    di.pci_subclass = 0x00;
    di.pci_revision = 0x00;
    di.pci_msi_nvecs = 32;
}

void
Corundum::dma_complete(nicbm::DMAOp &op)
{
    DMAOp *op_ = reinterpret_cast<DMAOp *>(&op);
    op_->ring->dmaDone(op_);
}

void
Corundum::eth_rx(uint8_t port, const void *data, size_t len)
{
    RxData *rx_data = new RxData;
    memcpy((void *)rx_data->data, data, len);
    rx_data->len = len;
    rxRing.rx(rx_data);
}

} //namespace corundum

using namespace corundum;

int main(int argc, char *argv[])
{
    Corundum dev;
    runner = new nicbm::Runner(dev);
    return runner->runMain(argc, argv);
}
