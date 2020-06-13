#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <signal.h>

#include <corundum_bm.h>
#include <nicsim.h>

static volatile int exiting = 0;
static struct CorundumRegs regs;

static void sigint_handler(int dummy)
{
    exiting = 1;
}

static volatile union cosim_pcie_proto_d2h *d2h_alloc(void)
{
    volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
    if (msg == NULL) {
        fprintf(stderr, "d2h_alloc: no entry available\n");
        abort();
    }
    return msg;
}

static uint64_t csr_read(uint64_t off)
{
    switch (off) {
        case   0x00: return 32; /* firmware id */
        case   0x04: return 1; /* firmware version */
        case   0x08: return 0x43215678; /* board id */
        case   0x0c: return 0x1; /* board version */
        case   0x10: return 1; /* phc count */
        case   0x14: return 0x200; /* phc offset */
        case   0x18: return 0x80; /* phc stride */
        case   0x20: return 1; /* if_count */
        case   0x24: return 0x80000; /* if stride */
        case   0x2c: return 0x80000; /* if csr offset */
        case  0x200: return 0x1; /* phc features */
        default:
            fprintf(stderr, "csr_read(%lu) unimplemented\n", off);
            return 0;
    }
}

static void csr_write(uint64_t off, uint64_t val)
{
}

static void read_complete(uint64_t req_id, void *val, uint16_t len)
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

static void h2d_read(volatile struct cosim_pcie_proto_h2d_read *read)
{
    printf("read(bar=0x%x, off=0x%lx, len=%u)\n", read->bar, read->offset, read->len);
    if (read->offset < 0x80000) {
        uint64_t val = csr_read(read->offset);
        read_complete(read->req_id, &val, read->len);
    } else {
        switch (read->offset - 0x80000) {
        case REG_A:
            read_complete(read->req_id, &regs.reg_a, read->len);
            break;
        case REG_B:
            read_complete(read->req_id, &regs.reg_b, read->len);
            break;
        case REG_C:
            read_complete(read->req_id, &regs.reg_c, read->len);
            break;
        case REG_D:
            read_complete(read->req_id, &regs.reg_d, read->len);
            break;
        case REG_E:
            read_complete(read->req_id, &regs.reg_e, read->len);
            break;
        case REG_F:
            read_complete(read->req_id, &regs.reg_f, read->len);
            break;
        case REG_G:
            read_complete(read->req_id, &regs.reg_g, read->len);
            break;
        case REG_H:
            read_complete(read->req_id, &regs.reg_h, read->len);
            break;
        case REG_I:
            read_complete(read->req_id, &regs.reg_i, read->len);
            break;
        case REG_J:
            read_complete(read->req_id, &regs.reg_j, read->len);
            break;
        case REG_K:
            read_complete(read->req_id, &regs.reg_k, read->len);
            break;
        case REG_L:
            read_complete(read->req_id, &regs.reg_l, read->len);
            break;
        case REG_M:
            read_complete(read->req_id, &regs.reg_m, read->len);
            break;
        case REG_N:
            read_complete(read->req_id, &regs.reg_n, read->len);
            break;
        case REG_O:
            read_complete(read->req_id, &regs.reg_o, read->len);
            break;
        default:
            fprintf(stderr, "unimplemented read at off=0x%lx len=%u\n", read->offset, read->len);
            uint64_t val = 0;
            read_complete(read->req_id, &val, read->len);
            break;
        }
    }
}

static void h2d_write(volatile struct cosim_pcie_proto_h2d_write *write)
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
