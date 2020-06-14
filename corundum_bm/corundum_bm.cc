#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <signal.h>

#include "corundum_bm.h"

extern "C" {
    #include <nicsim.h>
}

Corundum::Corundum()
{
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
            this->eqRing.setSizeLog(val & 0xFF);
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
            this->txRing.setSizeLog(val & 0xFF);
            break;
        case TX_QUEUE_INTERRUPT_INDEX_REG:
            this->txRing.setIndex(val);
            break;
        case TX_QUEUE_HEAD_PTR_REG:
            this->txRing.setHeadPtr(val);
            break;
        case TX_QUEUE_TAIL_PTR_REG:
            this->txRing.setTailPtr(val);
            break;
        default:
            fprintf(stderr, "Unknown register write %lx\n", addr);
            abort();
    }
}

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

static void
read_complete(uint64_t req_id, void *val, uint16_t len)
{
    volatile union cosim_pcie_proto_d2h *msg;
    volatile struct cosim_pcie_proto_d2h_readcomp *rc;

    msg = d2h_alloc();
    rc = &msg->readcomp;

    memcpy((void *)rc->data, val, len);
    rc->req_id = req_id;

    //WMB();
    rc->own_type = COSIM_PCIE_PROTO_D2H_MSG_READCOMP |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

static void
h2d_read(volatile struct cosim_pcie_proto_h2d_read *read)
{
    printf("read(bar=0x%x, off=0x%lx, len=%u)\n", read->bar, read->offset, read->len);
    if (read->offset < 0x80000) {
        uint64_t val = csr_read(read->offset);
        read_complete(read->req_id, &val, read->len);
    } else {
    }
}

static void
h2d_write(volatile struct cosim_pcie_proto_h2d_write *write)
{
    uint64_t val = 0;
    memcpy(&val, (void *)write->data, write->len);

    if (write->offset < 0x80000) {
        volatile union cosim_pcie_proto_d2h *msg;
        volatile struct cosim_pcie_proto_d2h_writecomp *wc;

        msg = d2h_alloc();
        wc = &msg->writecomp;

        printf("write(bar=0x%x, off=0x%lx, len=%u)\n", write->bar, write->offset, write->len);

        csr_write(write->offset, val);
        wc->req_id = write->req_id;

        //WMB();
        wc->own_type = COSIM_PCIE_PROTO_D2H_MSG_WRITECOMP |
            COSIM_PCIE_PROTO_D2H_OWN_HOST;
    } else {
        fprintf(stderr, "unimplemented write at off=0x%lx\n", write->offset);
    }
}

static void h2d_readcomp(volatile struct cosim_pcie_proto_h2d_readcomp *rc)
{
    printf("read complete(req_id=%lu)\n", rc->req_id);
}

static void h2d_writecomp(volatile struct cosim_pcie_proto_h2d_writecomp *wc)
{
    printf("write complete(req_id=%lu\n", wc->req_id);
}

static void n2d_recv(volatile struct cosim_eth_proto_n2d_recv *recv)
{
    printf("RX recv(port=%u, len=%u)\n", recv->port, recv->len);
}

static void poll_h2d(void)
{
    volatile union cosim_pcie_proto_h2d *msg = nicif_h2d_poll();
    uint8_t type;

    if (msg == NULL)
        return;

    type = msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_MSG_MASK;
    switch (type) {
        case COSIM_PCIE_PROTO_H2D_MSG_READ:
            h2d_read(&msg->read);
            break;

        case COSIM_PCIE_PROTO_H2D_MSG_WRITE:
            h2d_write(&msg->write);
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
            n2d_recv(&msg->recv);
            break;

        default:
            fprintf(stderr, "poll_n2d: unsupported type=%u", t);
    }

    nicif_n2d_done(msg);
    nicif_n2d_next();
}

int main(int argc, char *argv[])
{
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
                NULL, &sync_eth_en,
                "/dev/shm/dummy_nic_shm")) {
        return EXIT_FAILURE;
    }

    signal(SIGINT, sigint_handler);

    memset(&regs, 0, sizeof(regs));

    while (!exiting) {
        poll_h2d();
        poll_n2d();
    }

    nicsim_cleanup();
    return 0;
}
