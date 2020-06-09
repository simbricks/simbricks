/*
 * Copyright 2020 Max Planck Institute for Software Systems
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#include <fcntl.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/un.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>
#include <linux/if.h>
#include <linux/if_tun.h>

#include <cosim_eth_proto.h>

static uint8_t *d2n_queue;
static size_t d2n_pos;
static size_t d2n_elen;
static size_t d2n_enum;

static uint8_t *n2d_queue;
static size_t n2d_pos;
static size_t n2d_elen;
static size_t n2d_enum;

static int tap_fd;

int uxsocket_connect(const char *path)
{
    int fd;
    struct sockaddr_un saun;

    /* prepare and connect socket */
    memset(&saun, 0, sizeof(saun));
    saun.sun_family = AF_UNIX;
    strcpy(saun.sun_path, "/tmp/cosim-eth");

    if ((fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
        perror("socket failed");
        return -1;
    }

    if (connect(fd, (struct sockaddr *) &saun, sizeof(saun)) != 0) {
        perror("connect failed");
        return -1;
    }

    return fd;
}

int uxsocket_recv(int fd, void *data, size_t len, int *pfd)
{
    int *ppfd;
    ssize_t ret;
    struct cmsghdr *cmsg;
    union {
        char buf[CMSG_SPACE(sizeof(int))];
        struct cmsghdr align;
    } u;
    struct iovec iov = {
        .iov_base = data,
        .iov_len = len,
    };
    struct msghdr msg = {
        .msg_name = NULL,
        .msg_namelen = 0,
        .msg_iov = &iov,
        .msg_iovlen = 1,
        .msg_control = u.buf,
        .msg_controllen = sizeof(u.buf),
        .msg_flags = 0,
    };

    if ((ret = recvmsg(fd, &msg, 0)) != (ssize_t) len) {
        perror("recvmsg failed");
        return -1;
    }

    cmsg = CMSG_FIRSTHDR(&msg);
    ppfd = (int *) CMSG_DATA(cmsg);
    if (msg.msg_controllen <= 0 || cmsg->cmsg_len != CMSG_LEN(sizeof(int))) {
        fprintf(stderr, "accessing ancillary data failed\n");
        return -1;
    }

    *pfd = *ppfd;
    return 0;
}

void *shm_map(int shm_fd)
{
    void *p;
    struct stat statbuf;

    if (fstat(shm_fd, &statbuf) != 0) {
        perror("shm_map: fstat failed");
        return NULL;
    }

    p = mmap(NULL, statbuf.st_size, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd,
            0);
    if (p == MAP_FAILED) {
        perror("shm_map: mmap failed");
        return NULL;
    }

    return p;
}

static int tap_open(const char *name)
{
    struct ifreq ifr;
    int fd;

    if ((fd = open("/dev/net/tun", O_RDWR)) < 0) {
        perror("tap_open: open failed");
        return -1;
    }

    memset(&ifr, 0, sizeof(ifr));
    ifr.ifr_flags = IFF_TAP | IFF_NO_PI;
    strncpy(ifr.ifr_name, name, IFNAMSIZ);

    if (ioctl(fd, TUNSETIFF, &ifr) != 0) {
        perror("tap_open: ioctl failed");
        close(fd);
        return -1;
    }

    return fd;
}

static void d2n_send(volatile struct cosim_eth_proto_d2n_send *s)
{

    if (write(tap_fd, (void *) s->data, s->len) != (ssize_t) s->len) {
        perror("d2n_send: send failed");
    }
    /*uint16_t i;
    printf("packet [len=%u]:", s->len);
    for (i = 0; i < s->len; i++) {
        printf(" %02x", s->data[i]);
    }
    printf("\n");*/
}

static void poll_d2n(void)
{
    uint8_t type;
    volatile union cosim_eth_proto_d2n *msg =
        (volatile union cosim_eth_proto_d2n *)
        (d2n_queue + d2n_pos * d2n_elen);

    /* message not ready */
    if ((msg->dummy.own_type & COSIM_ETH_PROTO_D2N_OWN_MASK) !=
            COSIM_ETH_PROTO_D2N_OWN_NET)
        return;

    type = msg->dummy.own_type & COSIM_ETH_PROTO_D2N_MSG_MASK;
    switch (type) {
        case COSIM_ETH_PROTO_D2N_MSG_SEND:
            d2n_send(&msg->send);
            break;

        default:
            fprintf(stderr, "poll_d2n: unsupported type=%u\n", type);
    }

    msg->dummy.own_type = (msg->dummy.own_type & COSIM_ETH_PROTO_D2N_MSG_MASK)
        | COSIM_ETH_PROTO_D2N_OWN_DEV;
    d2n_pos = (d2n_pos + 1) % d2n_enum;
}

int main(int argc, char *argv[])
{
    struct cosim_eth_proto_dev_intro di;
    struct cosim_eth_proto_net_intro ni;
    int cfd, shm_fd;
    void *p;

    if (argc != 2) {
        fprintf(stderr, "Usage: net_tap TAP_DEVICE_NAME\n");
        return EXIT_FAILURE;
    }

    if ((tap_fd = tap_open(argv[1])) < 0) {
        return -1;
    }

    if ((cfd = uxsocket_connect("/tmp/cosim-eth")) < 0) {
        return -1;
    }

    memset(&ni, 0, sizeof(ni));
    if (send(cfd, &ni, sizeof(ni), 0) != sizeof(ni)) {
        perror("sending net intro failed");
        return -1;
    }

    if (uxsocket_recv(cfd, &di, sizeof(di), &shm_fd)) {
        return -1;
    }

    if ((p = shm_map(shm_fd)) == NULL) {
        return -1;
    }
    close(shm_fd);

    d2n_queue = (uint8_t *) p + di.d2n_offset;
    n2d_queue = (uint8_t *) p + di.n2d_offset;
    d2n_elen = di.d2n_elen;
    n2d_elen = di.n2d_elen;
    d2n_enum = di.d2n_nentries;
    n2d_enum = di.n2d_nentries;
    d2n_pos = n2d_pos = 0;

    printf("start polling\n");
    while (1) {
        poll_d2n();
    }
    return 0;
}
