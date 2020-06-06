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

#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <sys/un.h>
#include <sys/socket.h>
#include <sys/mman.h>
#include <unistd.h>

#include "../proto/cosim_pcie_proto.h"

#define D2H_ELEN (4096 + 64)
#define D2H_ENUM 1024

#define H2D_ELEN (64)
#define H2D_ENUM 1024

static int uxsocket_init(const char *path)
{
    int fd;
    struct sockaddr_un saun;

    if ((fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
        perror("uxsocket_init: socket failed");
        goto error_exit;
    }

    memset(&saun, 0, sizeof(saun));
    saun.sun_family = AF_UNIX;
    memcpy(saun.sun_path, path, strlen(path));
    if (bind(fd, (struct sockaddr *) &saun, sizeof(saun))) {
        perror("uxsocket_init: bind failed");
        goto error_close;
    }

    if (listen(fd, 5)) {
        perror("uxsocket_init: listen failed");
        goto error_close;
    }

    return fd;

error_close:
    close(fd);
error_exit:
    return -1;
}

static int uxsocket_send(int connfd, void *data, size_t len, int fd)
{
    ssize_t tx;
    struct iovec iov = {
        .iov_base = data,
        .iov_len = len,
    };
    union {
        char buf[CMSG_SPACE(sizeof(int))];
        struct cmsghdr align;
    } u;
    struct msghdr msg = {
        .msg_name = NULL,
        .msg_namelen = 0,
        .msg_iov = &iov,
        .msg_iovlen = 1,
        .msg_control = u.buf,
        .msg_controllen = 0,
        .msg_flags = 0,
    };
    struct cmsghdr *cmsg = &u.align;

    if (fd >= 0) {
        msg.msg_controllen = sizeof(u.buf);

        cmsg->cmsg_level = SOL_SOCKET;
        cmsg->cmsg_type = SCM_RIGHTS;
        cmsg->cmsg_len = CMSG_LEN(sizeof(int));

        *(int *) CMSG_DATA(cmsg) = fd;
    }

    if((tx = sendmsg(connfd, &msg, 0)) != (ssize_t) len) {
        fprintf(stderr, "tx == %zd\n", tx);
        return -1;
    }

    return 0;
}

static int shm_create(const char *path, size_t size, void **addr)
{
    int fd;
    void *p;

    if ((fd = open(path, O_CREAT | O_RDWR, 0666)) == -1) {
        perror("util_create_shmsiszed: open failed");
        goto error_out;
    }
    if (ftruncate(fd, size) != 0) {
        perror("util_create_shmsiszed: ftruncate failed");
        goto error_remove;
    }

    if ((p = mmap(NULL, size, PROT_READ | PROT_WRITE,
        MAP_SHARED | MAP_POPULATE, fd, 0)) == (void *) -1)
    {
        perror("util_create_shmsiszed: mmap failed");
        goto error_remove;
    }

    memset(p, 0, size);

    *addr = p;
    return fd;

error_remove:
    close(fd);
    unlink(path);
error_out:
    return -1;
}

int main(int argc, char *argv[])
{
    int shm_fd, pci_lfd, pci_cfd;
    size_t d2h_off, h2d_off;
    void *shmptr;

    if ((shm_fd = shm_create("/dev/shm/dummy_nic_shm", 32 * 1024 * 1024, &shmptr)) < 0) {
        return EXIT_FAILURE;
    }

    if ((pci_lfd = uxsocket_init("/tmp/cosim-pci")) < 0) {
        return EXIT_FAILURE;
    }

    if ((pci_cfd = accept(pci_lfd, NULL, NULL)) < 0) { 
        perror("accept pci_lfd failed");
        return EXIT_FAILURE;
    }
    printf("connection accepted\n");

    d2h_off = 0;
    h2d_off = (uint64_t) D2H_ELEN * D2H_ENUM;

    struct cosim_pcie_proto_dev_intro di;
    memset(&di, 0, sizeof(di));

    di.d2h_offset = d2h_off;
    di.d2h_elen = D2H_ELEN;
    di.d2h_nentries = D2H_ENUM;

    di.h2d_offset = h2d_off;
    di.h2d_elen = H2D_ELEN;
    di.h2d_nentries = H2D_ENUM;

    di.bars[0].len = 0x1000;
    di.bars[0].flags = COSIM_PCIE_PROTO_BAR_64;

    di.bars[2].len = 128;
    di.bars[2].flags = COSIM_PCIE_PROTO_BAR_IO;

    if (uxsocket_send(pci_cfd, &di, sizeof(di), shm_fd)) {
        return EXIT_FAILURE;
    }
    printf("connection sent\n");


    struct cosim_pcie_proto_host_intro hi;
    if (recv(pci_cfd, &hi, sizeof(hi), 0) != sizeof(hi)) {

        return EXIT_FAILURE;
    }
    printf("host info received\n");

    while (1) {
        pause();
    }
    close(pci_lfd);

    return 0;
}
