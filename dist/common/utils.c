/*
 * Copyright 2021 Max Planck Institute for Software Systems, and
 * National University of Singapore
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

#include "dist/common/utils.h"

#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

int UxsocketInit(const char *path) {
  int fd;
  struct sockaddr_un saun;

  if ((fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
    perror("uxsocket_init: socket failed");
    goto error_exit;
  }

  memset(&saun, 0, sizeof(saun));
  saun.sun_family = AF_UNIX;
  memcpy(saun.sun_path, path, strlen(path));
  if (bind(fd, (struct sockaddr *)&saun, sizeof(saun))) {
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

int UxsocketConnect(const char *path) {
  int fd;
  struct sockaddr_un saun;

  /* prepare and connect socket */
  memset(&saun, 0, sizeof(saun));
  saun.sun_family = AF_UNIX;
  strcpy(saun.sun_path, path);

  if ((fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
    perror("socket failed");
    return -1;
  }

  if (connect(fd, (struct sockaddr *)&saun, sizeof(saun)) != 0) {
    perror("connect failed");
    return -1;
  }

  return fd;
}

int UxsocketRecvFd(int fd, void *data, size_t len, int *pfd) {
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
  ppfd = (int *)CMSG_DATA(cmsg);
  if (msg.msg_controllen <= 0 || cmsg->cmsg_len != CMSG_LEN(sizeof(int))) {
    fprintf(stderr, "accessing ancillary data failed\n");
    return -1;
  }

  *pfd = *ppfd;
  return 0;
}

int UxsocketSendFd(int connfd, void *data, size_t len, int fd) {
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

    *(int *)CMSG_DATA(cmsg) = fd;
  }

  if ((tx = sendmsg(connfd, &msg, 0)) != (ssize_t)len) {
    fprintf(stderr, "tx == %zd\n", tx);
    return -1;
  }

  return 0;
}

int ShmCreate(const char *path, size_t size, void **addr) {
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

  if ((p = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_POPULATE,
                fd, 0)) == (void *)-1) {
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

void *ShmMap(int shm_fd, size_t *psize) {
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

  *psize = statbuf.st_size;
  return p;
}

