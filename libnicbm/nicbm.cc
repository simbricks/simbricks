#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <signal.h>
#include <cassert>

#include <nicbm.h>

//#define DEBUG_NICBM 1

#define SYNC_PERIOD (500 * 1000ULL) // 500ns
#define PCI_LATENCY (500 * 1000ULL) // 500ns
#define ETH_LATENCY (500 * 1000ULL) // 500ns


using namespace nicbm;

static volatile int exiting = 0;

static uint64_t main_time = 0;


static void sigint_handler(int dummy)
{
    exiting = 1;
}

static void sigusr1_handler(int dummy)
{
    fprintf(stderr, "main_time = %lu\n", main_time);
}

volatile union cosim_pcie_proto_d2h *Runner::d2h_alloc(void)
{
    volatile union cosim_pcie_proto_d2h *msg =
        nicsim_d2h_alloc(&nsparams, main_time);
    if (msg == NULL) {
        fprintf(stderr, "d2h_alloc: no entry available\n");
        abort();
    }
    return msg;
}

volatile union cosim_eth_proto_d2n *Runner::d2n_alloc(void)
{
    volatile union cosim_eth_proto_d2n *msg =
        nicsim_d2n_alloc(&nsparams, main_time);
    if (msg == NULL) {
        fprintf(stderr, "d2n_alloc: no entry available\n");
        abort();
    }
    return msg;
}

void Runner::issue_dma(DMAOp &op)
{
    volatile union cosim_pcie_proto_d2h *msg = d2h_alloc();
#ifdef DEBUG_NICBM
    printf("nicbm: issue dma op %p addr %lx len %zu\n", &op, op.dma_addr,
            op.len);
#endif

    if (op.write) {
        volatile struct cosim_pcie_proto_d2h_write *write = &msg->write;
        write->req_id = (uintptr_t) &op;
        write->offset = op.dma_addr;
        write->len = op.len;
        memcpy((void *)write->data, (void *)op.data, op.len);
        // WMB();
        write->own_type = COSIM_PCIE_PROTO_D2H_MSG_WRITE |
            COSIM_PCIE_PROTO_D2H_OWN_HOST;
    } else {
        volatile struct cosim_pcie_proto_d2h_read *read = &msg->read;
        read->req_id = (uintptr_t) &op;
        read->offset = op.dma_addr;
        read->len = op.len;
        // WMB();
        read->own_type = COSIM_PCIE_PROTO_D2H_MSG_READ |
            COSIM_PCIE_PROTO_D2H_OWN_HOST;
    }
}

void Runner::msi_issue(uint8_t vec)
{
    volatile union cosim_pcie_proto_d2h *msg = d2h_alloc();
#ifdef DEBUG_NICBM
    printf("nicbm: issue MSI interrupt vec %u\n", vec);
#endif
    volatile struct cosim_pcie_proto_d2h_interrupt *intr = &msg->interrupt;
    intr->vector = vec;
    intr->inttype = COSIM_PCIE_PROTO_INT_MSI;

    // WMB();
    intr->own_type = COSIM_PCIE_PROTO_D2H_MSG_INTERRUPT |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

void Runner::h2d_read(volatile struct cosim_pcie_proto_h2d_read *read)
{
    volatile union cosim_pcie_proto_d2h *msg;
    volatile struct cosim_pcie_proto_d2h_readcomp *rc;

    msg = d2h_alloc();
    rc = &msg->readcomp;

    dev.reg_read(read->bar, read->offset, (void *) rc->data, read->len);
    rc->req_id = read->req_id;

#ifdef DEBUG_NICBM
    uint64_t dbg_val = 0;
    memcpy(&dbg_val, (const void *) rc->data, read->len <= 8 ? read->len : 8);
    printf("nicbm: read(off=0x%lx, len=%u, val=0x%lx)\n", read->offset,
            read->len, dbg_val);
#endif

    //WMB();
    rc->own_type = COSIM_PCIE_PROTO_D2H_MSG_READCOMP |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

void Runner::h2d_write(volatile struct cosim_pcie_proto_h2d_write *write)
{
    volatile union cosim_pcie_proto_d2h *msg;
    volatile struct cosim_pcie_proto_d2h_writecomp *wc;

    msg = d2h_alloc();
    wc = &msg->writecomp;

#ifdef DEBUG_NICBM
    uint64_t dbg_val = 0;
    memcpy(&dbg_val, (const void *) write->data, write->len <= 8 ? write->len : 8);
    printf("nicbm: write(off=0x%lx, len=%u, val=0x%lx)\n", write->offset,
            write->len, dbg_val);
#endif
    dev.reg_write(write->bar, write->offset, (void *) write->data, write->len);
    wc->req_id = write->req_id;

    //WMB();
    wc->own_type = COSIM_PCIE_PROTO_D2H_MSG_WRITECOMP |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

void Runner::h2d_readcomp(volatile struct cosim_pcie_proto_h2d_readcomp *rc)
{
    DMAOp *op = (DMAOp *)(uintptr_t)rc->req_id;

#ifdef DEBUG_NICBM
    printf("nicbm: completed dma read op %p addr %lx len %zu\n", op,
            op->dma_addr, op->len);
#endif

    memcpy(op->data, (void *)rc->data, op->len);
    dev.dma_complete(*op);
}

void Runner::h2d_writecomp(volatile struct cosim_pcie_proto_h2d_writecomp *wc)
{
    DMAOp *op = (DMAOp *)(uintptr_t)wc->req_id;

#ifdef DEBUG_NICBM
    printf("nicbm: completed dma write op %p addr %lx len %zu\n", op,
            op->dma_addr, op->len);
#endif

    dev.dma_complete(*op);
}

void Runner::eth_recv(volatile struct cosim_eth_proto_n2d_recv *recv)
{
#ifdef DEBUG_NICBM
    printf("nicbm: eth rx: port %u len %u\n", recv->port, recv->len);
#endif

    dev.eth_rx(recv->port, (void *) recv->data, recv->len);
}

void Runner::eth_send(const void *data, size_t len)
{
#ifdef DEBUG_NICBM
    printf("nicbm: eth tx: len %zu\n", len);
#endif

    volatile union cosim_eth_proto_d2n *msg = d2n_alloc();
    volatile struct cosim_eth_proto_d2n_send *send = &msg->send;
    send->port = 0; // single port
    send->len = len;
    memcpy((void *)send->data, data, len);
    send->own_type = COSIM_ETH_PROTO_D2N_MSG_SEND |
        COSIM_ETH_PROTO_D2N_OWN_NET;
}

void Runner::poll_h2d()
{
    volatile union cosim_pcie_proto_h2d *msg =
        nicif_h2d_poll(&nsparams, main_time);
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

        case COSIM_PCIE_PROTO_H2D_MSG_SYNC:
            break;

        default:
            fprintf(stderr, "poll_h2d: unsupported type=%u\n", type);
    }

    nicif_h2d_done(msg);
    nicif_h2d_next();
}

void Runner::poll_n2d()
{
    volatile union cosim_eth_proto_n2d *msg =
        nicif_n2d_poll(&nsparams, main_time);
    uint8_t t;

    if (msg == NULL)
        return;

    t = msg->dummy.own_type & COSIM_ETH_PROTO_N2D_MSG_MASK;
    switch (t) {
        case COSIM_ETH_PROTO_N2D_MSG_RECV:
            eth_recv(&msg->recv);
            break;

        case COSIM_ETH_PROTO_N2D_MSG_SYNC:
            break;

        default:
            fprintf(stderr, "poll_n2d: unsupported type=%u", t);
    }

    nicif_n2d_done(msg);
    nicif_n2d_next();
}

Runner::Runner(Device &dev_)
    : dev(dev_)
{
}

int Runner::runMain(int argc, char *argv[])
{
    uint64_t next_ts;

    if (argc != 4 && argc != 5) {
        fprintf(stderr, "Usage: corundum_bm PCI-SOCKET ETH-SOCKET "
                "SHM [START-TICK]\n");
        return EXIT_FAILURE;
    }
    if (argc == 5)
        main_time = strtoull(argv[4], NULL, 0);


    signal(SIGINT, sigint_handler);
    signal(SIGUSR1, sigusr1_handler);

    struct cosim_pcie_proto_dev_intro di;
    memset(&di, 0, sizeof(di));
    dev.setup_intro(di);

    nsparams.sync_pci = 1;
    nsparams.sync_eth = 1;
    nsparams.pci_socket_path = argv[1];
    nsparams.eth_socket_path = argv[2];
    nsparams.shm_path = argv[3];
    nsparams.pci_latency = PCI_LATENCY;
    nsparams.eth_latency = ETH_LATENCY;
    nsparams.sync_delay = SYNC_PERIOD;
    if (nicsim_init(&nsparams, &di)) {
        return EXIT_FAILURE;
    }
    fprintf(stderr, "sync_pci=%d sync_eth=%d\n", nsparams.sync_pci,
        nsparams.sync_eth);

    while (!exiting) {
        while (nicsim_sync(&nsparams, main_time)) {
            fprintf(stderr, "warn: nicsim_sync failed (t=%lu)\n", main_time);
        }

        do {
            poll_h2d();
            poll_n2d();
            next_ts = netsim_next_timestamp(&nsparams);
        } while ((nsparams.sync_pci || nsparams.sync_eth) &&
            next_ts <= main_time && !exiting);
        main_time = next_ts;
    }

    fprintf(stderr, "exit main_time: %lu\n", main_time);
    nicsim_cleanup();
    return 0;
}
