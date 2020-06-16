#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <signal.h>
#include <cassert>

#include "corundum_bm.h"

extern "C" {
    #include <nicsim.h>
    #include <netsim.h>
}

static void issue_dma_op(corundum::DMAOp *op);
static void eth_send(void *data, size_t len);

namespace corundum {

DescRing::DescRing()
    : active(false)
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

unsigned
DescRing::headPtr()
{
    return this->_headPtr;
}

unsigned
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
}

void
DescRing::setIndex(unsigned index)
{
    assert(!(index & QUEUE_CONT_MASK));
    this->_index = index & 0xFF;
}

void
DescRing::setHeadPtr(unsigned ptr)
{
    this->_headPtr = ptr;
}

void
DescRing::setTailPtr(unsigned ptr)
{
    this->_tailPtr = ptr;
}

void
DescRing::dmaDone(DMAOp *op)
{
    // No action by default
}

bool
DescRing::empty()
{
    return (this->_headPtr == this->_tailPtr);
}

TxRing::TxRing()
{
}

TxRing::~TxRing()
{
}

void
TxRing::setHeadPtr(unsigned ptr)
{
    DescRing::setHeadPtr(ptr);
    if (!empty()) {
        unsigned index = (this->_headPtr - 1) & this->_sizeMask;
        addr_t dma_addr = this->_dmaAddr + index * DESC_SIZE;
        /* Issue DMA read */
        DMAOp *op = new DMAOp;
        op->type = DMA_TYPE_DESC;
        op->dma_addr = dma_addr;
        op->len = DESC_SIZE;
        op->ring = this;
        op->tag = this->_headPtr;
        op->write = false;
        issue_dma_op(op);
    }
}

void
TxRing::dmaDone(DMAOp *op)
{
    assert(!op->write);
    switch (op->type) {
    case DMA_TYPE_DESC: {
        Desc *desc = (Desc *)op->data;
        op->type = DMA_TYPE_MEM;
        op->dma_addr = desc->addr;
        op->len = desc->len;
        op->write = false;
        issue_dma_op(op);
        break;
    }
    case DMA_TYPE_MEM:
        eth_send(op->data, op->len);
        // TODO: assume in order transmission
        this->_tailPtr = (unsigned)op->tag;
        delete op;
        break;
    default:
        fprintf(stderr, "Unknown DMA type %u\n", op->type);
        abort();
    }
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

void queueDisable();
Corundum::Corundum()
{
    this->port.setId(0);
    this->port.setFeatures(0x711);
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
Corundum::readReg(addr_t addr)
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
        case IF_REG_IF_ID:
            return 0;
        case IF_REG_IF_FEATURES:
            return 0x711;
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
        case TX_QUEUE_ACTIVE_LOG_SIZE_REG:
            return this->txRing.sizeLog();
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
Corundum::writeReg(addr_t addr, reg_t val)
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
            this->eqRing.setDMALower(val);
            break;
        case EVENT_QUEUE_BASE_ADDR_REG + 4:
            this->eqRing.setDMAUpper(val);
            break;
        case EVENT_QUEUE_ACTIVE_LOG_SIZE_REG:
            this->eqRing.setSizeLog(val);
            break;
        case EVENT_QUEUE_INTERRUPT_INDEX_REG:
            this->eqRing.setIndex(val);
            break;
        case EVENT_QUEUE_HEAD_PTR_REG:
            this->eqRing.setHeadPtr(val);
            break;
        case EVENT_QUEUE_TAIL_PTR_REG:
            this->eqRing.setTailPtr(val);
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

} //namespace corundum

using namespace corundum;

static volatile int exiting = 0;

static void
sigint_handler(int dummy)
{
    exiting = 1;
}

static volatile union cosim_pcie_proto_d2h *
d2h_alloc(void)
{
    volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
    if (msg == NULL) {
        fprintf(stderr, "d2h_alloc: no entry available\n");
        abort();
    }
    return msg;
}

static volatile union cosim_eth_proto_d2n *
d2n_alloc(void)
{
    volatile union cosim_eth_proto_d2n *msg = nicsim_d2n_alloc();
    if (msg == NULL) {
        fprintf(stderr, "d2n_alloc: no entry available\n");
        abort();
    }
    return msg;
}

static void
issue_dma_op(DMAOp *op)
{
    volatile union cosim_pcie_proto_d2h *msg = d2h_alloc();
    printf("issue dma op %p addr %lx len %u\n", op, op->dma_addr, op->len);

    if (op->write) {
        volatile struct cosim_pcie_proto_d2h_write *write = &msg->write;
        write->req_id = (uintptr_t)op;
        write->offset = op->dma_addr;
        write->len = op->len;
        memcpy((void *)write->data, op->data, op->len);
        // WMB();
        write->own_type = COSIM_PCIE_PROTO_D2H_MSG_WRITE |
            COSIM_PCIE_PROTO_D2H_OWN_HOST;
    } else {
        volatile struct cosim_pcie_proto_d2h_read *read = &msg->read;
        read->req_id = (uintptr_t)op;
        read->offset = op->dma_addr;
        read->len = op->len;
        // WMB();
        read->own_type = COSIM_PCIE_PROTO_D2H_MSG_READ |
            COSIM_PCIE_PROTO_D2H_OWN_HOST;
    }
}

static void
h2d_read(Corundum &nic, volatile struct cosim_pcie_proto_h2d_read *read)
{
    reg_t val = nic.readReg(read->offset);
    printf("read(off=0x%lx, len=%u, val=0x%x)\n", read->offset, read->len, val);

    volatile union cosim_pcie_proto_d2h *msg;
    volatile struct cosim_pcie_proto_d2h_readcomp *rc;

    msg = d2h_alloc();
    rc = &msg->readcomp;

    memcpy((void *)rc->data, &val, read->len);
    rc->req_id = read->req_id;

    //WMB();
    rc->own_type = COSIM_PCIE_PROTO_D2H_MSG_READCOMP |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

static void
h2d_write(Corundum &nic, volatile struct cosim_pcie_proto_h2d_write *write)
{
    reg_t val = 0;
    memcpy(&val, (void *)write->data, write->len);

    volatile union cosim_pcie_proto_d2h *msg;
    volatile struct cosim_pcie_proto_d2h_writecomp *wc;

    msg = d2h_alloc();
    wc = &msg->writecomp;

    printf("write(off=0x%lx, len=%u, val=0x%x)\n", write->offset, write->len, val);
    nic.writeReg(write->offset, val);
    wc->req_id = write->req_id;

    //WMB();
    wc->own_type = COSIM_PCIE_PROTO_D2H_MSG_WRITECOMP |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

static void h2d_readcomp(volatile struct cosim_pcie_proto_h2d_readcomp *rc)
{
    DMAOp *op = (DMAOp *)(uintptr_t)rc->req_id;
    memcpy(op->data, (void *)rc->data, op->len);
    op->ring->dmaDone(op);
}

static void h2d_writecomp(volatile struct cosim_pcie_proto_h2d_writecomp *wc)
{
    DMAOp *op = (DMAOp *)(uintptr_t)wc->req_id;
    op->ring->dmaDone(op);
}

static void eth_recv(volatile struct cosim_eth_proto_n2d_recv *recv)
{
    printf("RX recv(port=%u, len=%u)\n", recv->port, recv->len);
}

static void eth_send(void *data, size_t len)
{
    volatile union cosim_eth_proto_d2n *msg = d2n_alloc();
    volatile struct cosim_eth_proto_d2n_send *send = &msg->send;
    send->port = 0; // single port
    send->len = len;
    memcpy((void *)send->data, data, len);
    send->own_type = COSIM_ETH_PROTO_D2N_MSG_SEND |
        COSIM_ETH_PROTO_D2N_OWN_NET;
}

static void poll_h2d(Corundum &nic)
{
    volatile union cosim_pcie_proto_h2d *msg = nicif_h2d_poll();
    uint8_t type;

    if (msg == NULL)
        return;

    type = msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_MSG_MASK;
    switch (type) {
        case COSIM_PCIE_PROTO_H2D_MSG_READ:
            h2d_read(nic, &msg->read);
            break;

        case COSIM_PCIE_PROTO_H2D_MSG_WRITE:
            h2d_write(nic, &msg->write);
            break;

        case COSIM_PCIE_PROTO_H2D_MSG_READCOMP:
            h2d_readcomp(&msg->readcomp);
            break;

        case COSIM_PCIE_PROTO_H2D_MSG_WRITECOMP:
            h2d_writecomp(&msg->writecomp);
            break;

        default:
            fprintf(stderr, "poll_h2d: unsupported type=%u\n", type);
    }

    nicif_h2d_done(msg);
    nicif_h2d_next();
}

static void poll_n2d(void)
{
    volatile union cosim_eth_proto_n2d *msg = nicif_n2d_poll();
    uint8_t t;

    if (msg == NULL)
        return;

    t = msg->dummy.own_type & COSIM_ETH_PROTO_N2D_MSG_MASK;
    switch (t) {
        case COSIM_ETH_PROTO_N2D_MSG_RECV:
            eth_recv(&msg->recv);
            break;

        default:
            fprintf(stderr, "poll_n2d: unsupported type=%u", t);
    }

    nicif_n2d_done(msg);
    nicif_n2d_next();
}

int main(int argc, char *argv[])
{
    signal(SIGINT, sigint_handler);

    struct cosim_pcie_proto_dev_intro di;
    memset(&di, 0, sizeof(di));
    di.bars[0].len = 1 << 24;
    di.bars[0].flags = COSIM_PCIE_PROTO_BAR_64;
    di.pci_vendor_id = 0x5543;
    di.pci_device_id = 0x1001;
    di.pci_class = 0x02;
    di.pci_subclass = 0x00;
    di.pci_revision = 0x00;
    di.pci_msi_nvecs = 32;

    int sync_pci_en = 0, sync_eth_en = 0;
    if (nicsim_init(&di, "/tmp/cosim-pci", &sync_pci_en,
                "/tmp/cosim-eth", &sync_eth_en,
                "/dev/shm/dummy_nic_shm")) {
        return EXIT_FAILURE;
    }

    Corundum nic;

    while (!exiting) {
        poll_h2d(nic);
        poll_n2d();
    }

    nicsim_cleanup();
    return 0;
}
