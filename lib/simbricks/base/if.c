/*
 * Copyright 2022 Max Planck Institute for Software Systems, and
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

#define _GNU_SOURCE

#include "lib/simbricks/base/if.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#include <simbricks/base/proto.h>

enum ConnState {
  kConnClosed = 0,
  kConnListening,
  kConnConnecting,
  kConnAwaitHandshakeRxTx,
  kConnAwaitHandshakeRx,
  kConnAwaitHandshakeTx,
  kConnOpen,
};

int SimbricksBaseIfSHMPoolCreate(struct SimbricksBaseIfSHMPool *pool,
                                 const char *path, size_t pool_size) {
  pool->path = path;
  pool->size = pool_size;
  pool->pos = 0;

  if ((pool->fd = open(path, O_CREAT | O_RDWR, 0666)) == -1) {
    perror("SimbricksBaseIfSHMPoolCreate: open failed");
    return -1;
  }

  if (ftruncate(pool->fd, pool_size) != 0) {
    perror("SimbricksBaseIfSHMPoolCreate: ftruncate failed");
    close(pool->fd);
    return -1;
  }

  pool->base = mmap(NULL, pool_size, PROT_READ | PROT_WRITE,
                    MAP_SHARED | MAP_POPULATE, pool->fd, 0);
  if (pool->base == (void *)-1) {
    perror("SimbricksBaseIfSHMPoolCreate: mmap failed");
    return -1;
  }

  memset(pool->base, 0, pool_size);
  return 0;
}

int SimbricksBaseIfSHMPoolMapFd(struct SimbricksBaseIfSHMPool *pool, int fd) {
  struct stat statbuf;

  if (fstat(fd, &statbuf) != 0) {
    perror("SimbricksBaseIfSHMPoolMap: fstat failed");
    close(fd);
    return -1;
  }

  pool->base =
      mmap(NULL, statbuf.st_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (pool->base == MAP_FAILED) {
    perror("SimbricksBaseIfSHMPoolMap: mmap failed");
    return -1;
  }

  pool->fd = fd;
  pool->path = NULL;
  pool->pos = 0;
  pool->size = statbuf.st_size;
  return 0;
}

int SimbricksBaseIfSHMPoolMap(struct SimbricksBaseIfSHMPool *pool,
                              const char *path) {
  int fd;

  if ((fd = open(path, O_RDWR, 0666) == -1)) {
    perror("SimbricksBaseIfSHMPoolMap: open failed");
    return -1;
  }

  if (SimbricksBaseIfSHMPoolMapFd(pool, fd)) {
    close(fd);
    return -1;
  }
  return 0;
}

int SimbricksBaseIfSHMPoolUnmap(struct SimbricksBaseIfSHMPool *pool) {
  if (munmap(pool->base, pool->size)) {
    perror("SimbricksBaseIfSHMPoolUnmap: unmap failed");
    return -1;
  }
  close(pool->fd);

  pool->fd = -1;
  pool->base = NULL;
  pool->size = 0;
  return 0;
}

int SimbricksBaseIfSHMPoolUnlink(struct SimbricksBaseIfSHMPool *pool) {
  return unlink(pool->path);
}

void SimbricksBaseIfDefaultParams(struct SimbricksBaseIfParams *params) {
  params->link_latency = 500 * 1000;
  params->sync_interval = params->link_latency;
  params->sock_path = NULL;
  params->sync_mode = kSimbricksBaseIfSyncOptional;
  params->in_num_entries = params->out_num_entries = 8192;
  params->in_entries_size = params->out_entries_size = 2048;
  params->blocking_conn = false;
  params->upper_layer_proto = SIMBRICKS_PROTO_ID_BASE;
}

size_t SimbricksBaseIfSHMSize(struct SimbricksBaseIfParams *params) {
  return params->in_num_entries * params->in_entries_size +
         params->out_num_entries * params->out_entries_size;
}

int SimbricksBaseIfInit(struct SimbricksBaseIf *base_if,
                        struct SimbricksBaseIfParams *params) {
  /* ensure latency >= sync interval in synchronization case */
  bool must_check_sync = params->sync_mode == kSimbricksBaseIfSyncOptional ||
    params->sync_mode == kSimbricksBaseIfSyncRequired;
  if (must_check_sync && params->link_latency < params->sync_interval) {
    fprintf(stderr,
            "SimbricksBaseIfInit: latency must be larger or equal to sync"
            " interval\n");
    return -1;
  }
  memset(base_if, 0, sizeof(*base_if));
  base_if->params = *params;
  return 0;
}

static int AcceptOnBaseIf(struct SimbricksBaseIf *base_if) {
  int flags = (!base_if->params.blocking_conn ? SOCK_NONBLOCK : 0);
  base_if->conn_fd = accept4(base_if->listen_fd, NULL, NULL, flags);
  if (base_if->conn_fd >= 0) {
    close(base_if->listen_fd);
    base_if->listen_fd = -1;
    base_if->conn_state = kConnAwaitHandshakeRxTx;
    return 0;
  } else if (errno == EAGAIN || errno == EWOULDBLOCK) {
    return 1;
  } else {
    perror("AcceptOnBaseIf: accept4 failed");
    close(base_if->listen_fd);
    base_if->listen_fd = -1;
    base_if->conn_state = kConnClosed;
    return -1;
  }
}

int SimbricksBaseIfListen(struct SimbricksBaseIf *base_if,
                          struct SimbricksBaseIfSHMPool *pool) {
  struct sockaddr_un saun;
  int flags;
  struct SimbricksBaseIfParams *params = &base_if->params;

  /* make sure we have enough space in the memory pool */
  base_if->shm = pool;
  size_t in_len = params->in_num_entries * params->in_entries_size;
  size_t out_len = params->out_num_entries * params->out_entries_size;
  if (pool->pos + in_len + out_len > pool->size) {
    fprintf(stderr,
            "SimbricksBaseIfListen: not enough memory available in "
            "pool");
    return -1;
  }

  if ((base_if->listen_fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
    perror("SimbricksBaseIfListen: socket failed");
    return -1;
  }

  if (!params->blocking_conn) {
    flags = fcntl(base_if->listen_fd, F_GETFL);
    if (flags == -1 ||
        fcntl(base_if->listen_fd, F_SETFL, flags | O_NONBLOCK) < 0) {
      perror("SimbricksBaseIfListen: fcntl set nonblock failed");
      goto out_error;
    }
  }

  memset(&saun, 0, sizeof(saun));
  saun.sun_family = AF_UNIX;
  strncpy(saun.sun_path, params->sock_path, sizeof(saun.sun_path) - 1);
  if (bind(base_if->listen_fd, (struct sockaddr *)&saun, sizeof(saun))) {
    perror("SimbricksBaseIfListen: bind failed");
    goto out_error;
  }

  if (listen(base_if->listen_fd, 5)) {
    perror("SimbricksBaseIfListen: listen failed");
    goto out_error;
  }

  /* initialize queues */
  base_if->in_queue = pool->base + pool->pos;
  base_if->in_pos = 0;
  base_if->in_elen = params->in_entries_size;
  base_if->in_enum = params->in_num_entries;
  base_if->in_timestamp = 0;
  pool->pos += in_len;

  base_if->out_queue = pool->base + pool->pos;
  base_if->out_pos = 0;
  base_if->out_elen = params->out_entries_size;
  base_if->out_enum = params->out_num_entries;
  base_if->out_timestamp = 0;
  pool->pos += out_len;

  base_if->conn_state = kConnListening;
  base_if->listener = true;
  return (AcceptOnBaseIf(base_if) < 0 ? -1 : 0);

out_error:
  close(base_if->listen_fd);
  base_if->listen_fd = -1;
  return -1;
}

int SimbricksBaseIfConnect(struct SimbricksBaseIf *base_if) {
  struct sockaddr_un saun;
  int flags;
  struct SimbricksBaseIfParams *params = &base_if->params;

  base_if->listener = false;

  if ((base_if->conn_fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
    perror("SimbricksBaseIfConnect: socket failed");
    return -1;
  }

  if (!params->blocking_conn) {
    flags = fcntl(base_if->conn_fd, F_GETFL);
    if (flags == -1 ||
        fcntl(base_if->conn_fd, F_SETFL, flags | O_NONBLOCK) < 0) {
      perror("SimbricksBaseIfConnect: fcntl set nonblock failed");
      goto out_error;
    }
  }

  memset(&saun, 0, sizeof(saun));
  saun.sun_family = AF_UNIX;
  strncpy(saun.sun_path, params->sock_path, sizeof(saun.sun_path) - 1);

  int ret = connect(base_if->conn_fd, (struct sockaddr *)&saun, sizeof(saun));
  if (ret == 0) {
    base_if->conn_state = kConnAwaitHandshakeRxTx;
  } else if (errno == EAGAIN || errno == EWOULDBLOCK) {
    base_if->conn_state = kConnConnecting;
  } else {
    perror("SimbricksBaseIfConnect: connect failed");
    base_if->conn_state = kConnClosed;
    return -1;
  }

  return 0;

out_error:
  close(base_if->listen_fd);
  base_if->listen_fd = -1;
  return -1;
}

int SimbricksBaseIfConnected(struct SimbricksBaseIf *base_if) {
  switch (base_if->conn_state) {
    case kConnClosed:
      return -1;

    case kConnListening:
      return AcceptOnBaseIf(base_if);

    case kConnConnecting: {
      struct pollfd pfd;
      pfd.fd = base_if->conn_fd;
      pfd.events = POLLOUT;
      pfd.revents = 0;

      int ret = poll(&pfd, 1, 0);
      if (ret < 0 || (ret == 1 && pfd.revents != POLLOUT)) {
        perror("SimbricksBaseIfConnected: poll failed");
        close(base_if->conn_fd);
        base_if->conn_fd = -1;
        base_if->conn_state = kConnClosed;
        return -1;
      } else if (ret == 0) {
        return 1;
      }

      int status = 0;
      socklen_t slen = sizeof(status);
      if (getsockopt(base_if->conn_fd, SOL_SOCKET, SO_ERROR, &status, &slen) !=
          0) {
        perror("SimbricksBaseIfConnected: getsockopt failed");
        close(base_if->conn_fd);
        base_if->conn_fd = -1;
        base_if->conn_state = kConnClosed;
        return -1;
      }

      if (status == 0) {
        base_if->conn_state = kConnAwaitHandshakeRxTx;
        return 0;
      } else {
        close(base_if->conn_fd);
        base_if->conn_fd = -1;
        base_if->conn_state = kConnClosed;
        return -1;
      }
      break;
    }

    case kConnAwaitHandshakeRxTx: /* FALLTRHOUGH */
    case kConnAwaitHandshakeRx:   /* FALLTRHOUGH */
    case kConnAwaitHandshakeTx:   /* FALLTRHOUGH */
    case kConnOpen:
      /* the connection is fully established */
      return 0;

    default:
      fprintf(stderr, "SimbricksBaseIfConnected: unexpected conn state %u\n",
              base_if->conn_state);
      abort();
  }
}

int SimbricksBaseIfConnFd(struct SimbricksBaseIf *base_if) {
  if (base_if->conn_state == kConnListening) {
    return base_if->listen_fd;
  } else if (base_if->conn_state == kConnConnecting) {
    return base_if->conn_fd;
  } else {
    return -1;
  }
}

int SimbricksBaseIfConnsWait(struct SimbricksBaseIf **base_ifs, unsigned n) {
  unsigned i, n_wait;
  struct pollfd pfds[n];
  unsigned ids[n];

  do {
    /* prepare poll events */
    n_wait = 0;
    for (i = 0; i < n; i++) {
      struct SimbricksBaseIf *base_if = base_ifs[i];
      switch (base_if->conn_state) {
        case kConnListening:
          ids[n_wait] = i;
          pfds[n_wait].fd = base_if->listen_fd;
          pfds[n_wait].events = POLLIN;
          pfds[n_wait].revents = 0;
          n_wait++;
          break;

        case kConnConnecting:
          ids[n_wait] = i;
          pfds[n_wait].fd = base_if->conn_fd;
          pfds[n_wait].events = POLLOUT;
          pfds[n_wait].revents = 0;
          n_wait++;
          break;

        case kConnAwaitHandshakeRxTx: /* FALLTHROUGH */
        case kConnAwaitHandshakeRx:   /* FALLTHROUGH */
        case kConnAwaitHandshakeTx:   /* FALLTHROUGH */
        case kConnOpen:
          /* already connected, nothing to be done */
          break;

        default:
          /* closed or error came up */
          return -1;
      }
    }

    if (n_wait == 0)
      break;

    int ret = poll(pfds, n_wait, -1);
    if (ret < 0) {
      perror("SimbricksBaseIfConnsWait: poll failed");
      return -1;
    }

    for (i = 0; i < n; i++) {
      struct SimbricksBaseIf *bif = base_ifs[ids[i]];

      if ((pfds[i].revents & ~(POLLIN | POLLOUT)) != 0) {
        perror("SimbricksBaseIfConnsWait: error event");
        return -1;
      }

      ret = SimbricksBaseIfConnected(bif);
      if (ret < 0) {
        perror("SimbricksBaseIfConnsWait: connected failed");
        return -1;
      } else if (ret == 0) {
        n_wait--;
      }
    }
  } while (n_wait > 0);
  return 0;
}

/** Send intro. */
int SimbricksBaseIfIntroSend(struct SimbricksBaseIf *base_if,
                             const void *payload, size_t payload_len) {
  if (base_if->conn_state != kConnAwaitHandshakeRxTx &&
      base_if->conn_state != kConnAwaitHandshakeTx) {
    return -1;
  }

  struct iovec iov[2];
  union {
    char buf[CMSG_SPACE(sizeof(int))];
    struct cmsghdr align;
  } u;
  struct msghdr msg = {
      .msg_name = NULL,
      .msg_namelen = 0,
      .msg_iov = iov,
      .msg_iovlen = (payload_len > 0 ? 2 : 1),
      .msg_control = NULL,
      .msg_controllen = 0,
      .msg_flags = 0,
  };

  /* fill in payload iov entry */
  iov[1].iov_base = (void *)payload;
  iov[1].iov_len = payload_len;

  struct SimbricksProtoListenerIntro l_intro;
  struct SimbricksProtoConnecterIntro c_intro;
  if (base_if->listener) {
    l_intro.version = SIMBRICKS_PROTO_VERSION;
    l_intro.flags =
        (base_if->params.sync_mode == kSimbricksBaseIfSyncDisabled
             ? 0
             : (SIMBRICKS_PROTO_FLAGS_LI_SYNC |
                (base_if->params.sync_mode == kSimbricksBaseIfSyncRequired
                     ? SIMBRICKS_PROTO_FLAGS_LI_SYNC_FORCE
                     : 0)));

    l_intro.l2c_offset = base_if->out_queue - base_if->shm->base;
    l_intro.l2c_elen = base_if->out_elen;
    l_intro.l2c_nentries = base_if->out_enum;

    l_intro.c2l_offset = base_if->in_queue - base_if->shm->base;
    l_intro.c2l_elen = base_if->in_elen;
    l_intro.c2l_nentries = base_if->in_enum;

    l_intro.upper_layer_proto = base_if->params.upper_layer_proto;
    l_intro.upper_layer_intro_off = sizeof(l_intro);

    iov[0].iov_base = &l_intro;
    iov[0].iov_len = sizeof(l_intro);

    // listeners will also send the shm fd attached
    msg.msg_control = u.buf;
    msg.msg_controllen = sizeof(u.buf);

    struct cmsghdr *cmsg = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type = SCM_RIGHTS;
    cmsg->cmsg_len = CMSG_LEN(sizeof(int));
    *(int *)CMSG_DATA(cmsg) = base_if->shm->fd;
  } else {
    c_intro.version = SIMBRICKS_PROTO_VERSION;
    c_intro.flags =
        (base_if->params.sync_mode == kSimbricksBaseIfSyncDisabled
             ? 0
             : (SIMBRICKS_PROTO_FLAGS_CO_SYNC |
                (base_if->params.sync_mode == kSimbricksBaseIfSyncRequired
                     ? SIMBRICKS_PROTO_FLAGS_CO_SYNC_FORCE
                     : 0)));
    c_intro.upper_layer_proto = base_if->params.upper_layer_proto;
    c_intro.upper_layer_intro_off = sizeof(c_intro);

    iov[0].iov_base = &c_intro;
    iov[0].iov_len = sizeof(c_intro);
  }

  ssize_t ret = sendmsg(base_if->conn_fd, &msg, 0);
  if (ret < 0) {
    perror("SimbricksBaseIfIntroSend: sendmsg failed");
    return -1;
  } else if (ret != (ssize_t)(iov[0].iov_len + iov[1].iov_len)) {
    fprintf(stderr,
            "SimbricksBaseIfIntroSend: sendmsg was short, "
            "currently unsupported\n");
    return -1;
  }

  if (base_if->conn_state == kConnAwaitHandshakeTx) {
    base_if->conn_state = kConnOpen;
  } else if (base_if->conn_state == kConnAwaitHandshakeRxTx) {
    base_if->conn_state = kConnAwaitHandshakeRx;
  } else {
    fprintf(stderr,
            "SimbricksBaseIfIntroSend: connection in unexpected "
            "state at the end.\n");
    abort();
  }

  return 0;
}

/** Receive intro. */
int SimbricksBaseIfIntroRecv(struct SimbricksBaseIf *base_if, void *payload,
                             size_t *payload_len) {
  if (base_if->conn_state != kConnAwaitHandshakeRxTx &&
      base_if->conn_state != kConnAwaitHandshakeRx) {
    return -1;
  }

  uint8_t intro_buf[2048];

  struct iovec iov;
  iov.iov_base = intro_buf;
  iov.iov_len = sizeof(intro_buf);

  struct cmsghdr *cmsg;
  union {
    char buf[CMSG_SPACE(sizeof(int))];
    struct cmsghdr align;
  } u;

  struct msghdr msg = {
      .msg_name = NULL,
      .msg_namelen = 0,
      .msg_iov = &iov,
      .msg_iovlen = 1,
      .msg_control = NULL,
      .msg_controllen = 0,
      .msg_flags = 0,
  };

  if (!base_if->listener) {
    // connectors will also receive the shm fd attached
    msg.msg_control = u.buf;
    msg.msg_controllen = sizeof(u.buf);
  }

  ssize_t ret = recvmsg(base_if->conn_fd, &msg, 0);
  if (ret < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
    // no handshake available yet
    return 1;
  } else if (ret < 0) {
    perror("SimbricksBaseIfIntroRecv: recvmsg failed");
    return -1;
  }

  uint64_t version, upper_proto, upper_off;
  bool sync, sync_force;

  if (base_if->listener) {
    struct SimbricksProtoConnecterIntro *c_intro =
        (struct SimbricksProtoConnecterIntro *)intro_buf;
    sync = c_intro->flags & SIMBRICKS_PROTO_FLAGS_CO_SYNC;
    sync_force = c_intro->flags & SIMBRICKS_PROTO_FLAGS_CO_SYNC_FORCE;
    version = c_intro->version;
    upper_proto = c_intro->upper_layer_proto;
    upper_off = c_intro->upper_layer_intro_off;
  } else {
    struct SimbricksProtoListenerIntro *l_intro =
        (struct SimbricksProtoListenerIntro *)intro_buf;

    sync = l_intro->flags & SIMBRICKS_PROTO_FLAGS_LI_SYNC;
    sync_force = l_intro->flags & SIMBRICKS_PROTO_FLAGS_LI_SYNC_FORCE;
    version = l_intro->version;
    upper_proto = l_intro->upper_layer_proto;
    upper_off = l_intro->upper_layer_intro_off;
  }

  if (version != SIMBRICKS_PROTO_VERSION) {
    fprintf(stderr, "SimbricksBaseIfIntroRecv: unexpected version (%lx)\n",
            version);
    return -1;
  }

  if (upper_proto != base_if->params.upper_layer_proto) {
    fprintf(stderr,
            "SimbricksBaseIfIntroRecv: peer's upper layer proto (%lx) "
            "does not match ours (%lx)\n",
            upper_proto, base_if->params.upper_layer_proto);
    return -1;
  }

  if (sync_force && base_if->params.sync_mode == kSimbricksBaseIfSyncDisabled) {
    fprintf(stderr,
            "SimbricksBaseIfIntroRecv: peer forced sync but we haved "
            "it disabled.\n");
    return -1;
  } else if (!sync && !sync_force &&
             base_if->params.sync_mode == kSimbricksBaseIfSyncRequired) {
    fprintf(stderr,
            "SimbricksBaseIfIntroRecv: sync required locally, put peer "
            "offers no sync.\n");
    return -1;
  } else if (base_if->params.sync_mode == kSimbricksBaseIfSyncDisabled) {
    base_if->sync = false;
  } else {
    base_if->sync = sync || sync_force;
  }

  size_t upper_layer_len = (size_t)ret - upper_off;
  if (*payload_len < upper_layer_len) {
    fprintf(stderr,
            "SimbricksBaseIfIntroRecv: upper layer intro does not "
            "fit in provided buffer\n");
    return -1;
  }
  memcpy(payload, intro_buf + upper_off, upper_layer_len);
  *payload_len = upper_layer_len;

  if (!base_if->listener) {
    // handle shm setup
    struct SimbricksProtoListenerIntro *l_intro =
        (struct SimbricksProtoListenerIntro *)intro_buf;

    cmsg = CMSG_FIRSTHDR(&msg);
    if (msg.msg_controllen <= 0 || cmsg->cmsg_len != CMSG_LEN(sizeof(int))) {
      /* TODO fix error handling (leaking fds) */
      fprintf(stderr,
              "SimbricksBaseIfIntroRecv: getting shm fd failed (%zu) "
              "(%p != %zu)\n",
              msg.msg_controllen, cmsg, CMSG_LEN(sizeof(int)));
      return -1;
    }
    int shmfd = *(int *)CMSG_DATA(cmsg);
    if ((base_if->shm = calloc(1, sizeof(*base_if->shm))) == NULL) {
      fprintf(stderr, "SimbricksBaseIfIntroRecv: getting shm fd failed\n");
      return -1;
    }

    if (SimbricksBaseIfSHMPoolMapFd(base_if->shm, shmfd)) {
      fprintf(stderr, "SimbricksBaseIfIntroRecv: mapping shm failed\n");
      close(shmfd);
      free(base_if->shm);
      return -1;
    }

    base_if->out_queue = base_if->shm->base + l_intro->c2l_offset;
    base_if->out_elen = l_intro->c2l_elen;
    base_if->out_enum = l_intro->c2l_nentries;

    base_if->in_queue = base_if->shm->base + l_intro->l2c_offset;
    base_if->in_elen = l_intro->l2c_elen;
    base_if->in_enum = l_intro->l2c_nentries;
  }

  if (base_if->conn_state == kConnAwaitHandshakeRx) {
    base_if->conn_state = kConnOpen;
  } else if (base_if->conn_state == kConnAwaitHandshakeRxTx) {
    base_if->conn_state = kConnAwaitHandshakeTx;
  } else {
    fprintf(stderr,
            "SimbricksBaseIfIntroRecv: connection in unexpected "
            "state at the end.\n");
    abort();
  }

  return 0;
}

/** FD to wait on for intro events. */
int SimbricksBaseIfIntroFd(struct SimbricksBaseIf *base_if) {
  switch (base_if->conn_state) {
    case kConnAwaitHandshakeRxTx: /* FALLTRHOUGH */
    case kConnAwaitHandshakeRx:   /* FALLTRHOUGH */
    case kConnAwaitHandshakeTx:
      return base_if->conn_fd;

    default:
      return -1;
  }
}

int SimBricksBaseIfEstablish(struct SimBricksBaseIfEstablishData *ifs,
                             size_t n) {
  struct pollfd pfds[n];
  unsigned n_pfd;
  size_t established = 0;
  int ret;

  while (established < n) {
    size_t i;
    n_pfd = 0;
    established = 0;
    for (i = 0; i < n; i++) {
      struct SimbricksBaseIf *bif = ifs[i].base_if;

      // woops something went wrong on this connection
      if (bif->conn_state == kConnClosed) {
        fprintf(stderr,
                "SimBricksBaseIfEstablish: connection %zu is "
                "closed\n",
                i);
        return -1;
      }

      // check if it is connected yet (this might change that)
      ret = SimbricksBaseIfConnected(bif);
      if (ret < 0) {
        fprintf(stderr, "SimBricksBaseIfEstablish: connecting %zu failed\n", i);
        return -1;
      } else if (ret > 0) {
        pfds[n_pfd].fd = SimbricksBaseIfConnFd(bif);
        pfds[n_pfd].events =
            (bif->conn_state == kConnListening ? POLLIN : POLLOUT);
        pfds[n_pfd].revents = 0;
        n_pfd++;
        assert(n_pfd <= n);
      }

      // next check if we are now ready to send the handshake
      if ((bif->conn_state == kConnAwaitHandshakeTx ||
           bif->conn_state == kConnAwaitHandshakeRxTx) &&
          SimbricksBaseIfIntroSend(bif, ifs[i].tx_intro, ifs[i].tx_intro_len) !=
              0) {
        fprintf(stderr,
                "SimBricksBaseIfEstablish: Sending intro on %zu "
                "failed\n",
                i);
        return -1;
      }

      // finally check if we can receive the handshake now
      if (bif->conn_state == kConnAwaitHandshakeRx) {
        ret = SimbricksBaseIfIntroRecv(bif, ifs[i].rx_intro,
                                       &ifs[i].rx_intro_len);
        if (ret < 0) {
          fprintf(stderr,
                  "SimBricksBaseIfEstablish: Receiving intro on %zu "
                  "failed\n",
                  i);
          return -1;
        } else if (ret > 0) {
          pfds[n_pfd].fd = SimbricksBaseIfIntroFd(bif);
          pfds[n_pfd].events = POLLIN;
          pfds[n_pfd].revents = 0;
          n_pfd++;
          assert(n_pfd <= n);
        }
      }

      if (bif->conn_state == kConnOpen) {
        established++;
      }
    }

    if (n_pfd == 0 && established != n) {
      fprintf(stderr,
              "SimBricksBaseIfEstablish: no poll events to wait for "
              "but not all established (BUG)\n");
      abort();
    } else if (n_pfd > 0) {
      ret = poll(pfds, n_pfd, -1);
      if (ret < 0) {
        fprintf(stderr, "SimBricksBaseIfEstablish: poll failed\n");
        return -1;
      }
    }
  }

  return 0;
}

void SimbricksBaseIfClose(struct SimbricksBaseIf *base_if) {
  if (base_if->conn_state == kConnListening) {
    close(base_if->listen_fd);
    base_if->listen_fd = -1;
    base_if->conn_state = kConnClosed;
    return;
  } else if (base_if->conn_state == kConnClosed) {
    return;
  }

  if (base_if->conn_state == kConnOpen) {
    // send out termination message
    volatile union SimbricksProtoBaseMsg *msg;
    while ((msg = SimbricksBaseIfOutAlloc(base_if, UINT64_MAX)) == NULL) {
    }
    SimbricksBaseIfOutSend(base_if, msg, SIMBRICKS_PROTO_MSG_TYPE_TERMINATE);
  }

  close(base_if->conn_fd);
  base_if->conn_fd = -1;
  base_if->conn_state = kConnClosed;

  // TODO: if connecting end might need to unmap and free shm
}

void SimbricksBaseIfUnlink(struct SimbricksBaseIf *base_if) {
  // TODO
}
