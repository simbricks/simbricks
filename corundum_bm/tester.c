#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/mman.h>
#include <unistd.h>
#include <signal.h>
#include <fcntl.h>
#include <assert.h>

#include <nicsim.h>
#include <cosim_pcie_proto.h>

static uint8_t *d2h_queue;
static size_t d2h_pos;
static size_t d2h_elen;
static size_t d2h_enum;

static uint8_t *h2d_queue;
static size_t h2d_pos;
static size_t h2d_elen;
static size_t h2d_enum;

static void sigint_handler(int dummy)
{
    exit(1);
}

static int uxsocket_init()
{
    int cfd;

    if ((cfd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
        return -1;
    }

    struct sockaddr_un saun;
    memset(&saun, 0, sizeof(saun));
    saun.sun_family = AF_UNIX;
    memcpy(saun.sun_path, "/tmp/cosim-pci", strlen("/tmp/cosim-pci"));

    if (connect(cfd, (struct sockaddr *)&saun, sizeof(saun)) == -1) {
        close(cfd);
        return -1;
    }

    return cfd;
}

static int queue_create(const struct cosim_pcie_proto_dev_intro di)
{
    int fd = -1;
    if ((fd = open("/dev/shm/dummy_nic_shm", O_RDWR)) == -1) {
        perror("Failed to open shm file");
        goto error;
    }

    void *addr;
    if ((addr = mmap(NULL, 32 * 1024 * 1024, PROT_READ | PROT_WRITE,
                     MAP_SHARED | MAP_POPULATE, fd, 0)) == (void *)-1) {
        perror("mmap failed");
        goto error;
    }

    d2h_queue = (uint8_t *)addr + di.d2h_offset;
    d2h_pos = 0;
    d2h_elen = di.d2h_elen;
    d2h_enum = di.d2h_nentries;

    h2d_queue = (uint8_t *)addr + di.h2d_offset;
    h2d_pos = 0;
    h2d_elen = di.h2d_elen;
    h2d_enum = di.h2d_nentries;

    return 0;

error:
    if (fd > 0) {
        close(fd);
    }
    return -1;
}

volatile union cosim_pcie_proto_h2d *h2d_alloc()
{
    volatile union cosim_pcie_proto_h2d *msg =
        (volatile union cosim_pcie_proto_h2d *)
        (h2d_queue + h2d_pos * h2d_elen);

    if ((msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_OWN_MASK) !=
            COSIM_PCIE_PROTO_H2D_OWN_HOST) {
        fprintf(stderr, "cosim: failed to allocate h2d message\n");
        exit(1);
    }

    h2d_pos = (h2d_pos + 1) % h2d_enum;
    return msg;
}

volatile union cosim_pcie_proto_d2h *d2h_poll()
{
    volatile union cosim_pcie_proto_d2h *msg;

    msg = (volatile union cosim_pcie_proto_d2h *)
        (d2h_queue + d2h_pos * d2h_elen);
    if ((msg->dummy.own_type & COSIM_PCIE_PROTO_D2H_OWN_MASK) ==
            COSIM_PCIE_PROTO_D2H_OWN_DEV) {
        return NULL;
    }
    return msg;
}

void d2h_done(volatile union cosim_pcie_proto_d2h *msg)
{
    msg->dummy.own_type = (msg->dummy.own_type & COSIM_PCIE_PROTO_D2H_MSG_MASK) |
        COSIM_PCIE_PROTO_D2H_OWN_DEV;
    d2h_pos = (d2h_pos + 1) % d2h_enum;
}

static void dev_read(uint64_t offset, uint16_t len)
{
    volatile union cosim_pcie_proto_h2d *h2d_msg = h2d_alloc();
    volatile struct cosim_pcie_proto_h2d_read *read = &h2d_msg->read;
    read->req_id = 0xF;
    read->offset = offset;
    read->len = len;
    read->bar = 0;
    read->own_type = COSIM_PCIE_PROTO_H2D_MSG_READ | COSIM_PCIE_PROTO_H2D_OWN_DEV;

    volatile union cosim_pcie_proto_d2h *d2h_msg = NULL;
    while (d2h_msg == NULL) {
        d2h_msg = d2h_poll();
    }
    volatile struct cosim_pcie_proto_d2h_readcomp *rc;
    rc = &d2h_msg->readcomp;
    assert(rc->req_id == 0xF);
    printf("received readcomp with data ");
    for (int i = 0; i < read->len; i++) {
        printf("%x ", ((const uint8_t *)rc->data)[i]);
    }
    printf("\n");

    d2h_done(d2h_msg);
}

int main(int argc, char *argv[])
{
    signal(SIGINT, sigint_handler);

    int cfd;
    if ((cfd = uxsocket_init()) < 0) {
        fprintf(stderr, "Failed to open unix socket\n");
        return -1;
    }

    struct cosim_pcie_proto_dev_intro di;
    if (recv(cfd, &di, sizeof(di), 0) != sizeof(di)) {
        perror("Failed to receive dev_intro");
        close(cfd);
        return -1;
    }

    if (queue_create(di) != 0) {
        fprintf(stderr, "Failed to create shm queues\n");
        close(cfd);
        return -1;
    }

    struct cosim_pcie_proto_host_intro hi;
    hi.flags = COSIM_PCIE_PROTO_FLAGS_HI_SYNC;
    if (send(cfd, &hi, sizeof(hi), 0) != sizeof(hi)) {
        perror("Failed to send host_intro");
        close(cfd);
        return -1;
    }

    while (1) {
        int op_type;
        uint64_t offset;
        uint16_t len;
        printf("op type (0-read): ");
        scanf("%d", &op_type);
        printf("offset: ");
        scanf("%lx", &offset);
        printf("len: ");
        scanf("%hu", &len);
        switch (op_type) {
        case 0:
            dev_read(offset, len);
            break;
        default:
            fprintf(stderr, "Unimplemented type %u\n", op_type);
        }
    }

    close(cfd);
    return 0;
}
