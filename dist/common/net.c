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

#include "dist/common/net.h"

#include <assert.h>
#include <fcntl.h>
#include <getopt.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/mman.h>
#include <unistd.h>

#include <simbricks/proto/base.h>

#include "dist/common/utils.h"

static const uint64_t kPollReportThreshold = 128;
static const uint64_t kCleanReportThreshold = 128;
static const uint64_t kPollMax = 8;
static const uint64_t kCleanupMax = 16;

static size_t shm_size;
void *shm_base;
static int shm_fd = -1;
static size_t shm_alloc_off = 0;

size_t peer_num = 0;
struct Peer *peers = NULL;

static int epfd = -1;

int NetInit(const char *shm_path_, size_t shm_size_, int epfd_) {
  shm_size = shm_size_;
  if ((shm_fd = ShmCreate(shm_path_, shm_size_, &shm_base)) < 0)
    return 1;

  epfd = epfd_;
  return 0;
}

static int ShmAlloc(size_t size, uint64_t *off) {
#ifdef DEBUG
  fprintf(stderr, "ShmAlloc(%zu)\n", size);
#endif

  if (shm_alloc_off + size > shm_size) {
    fprintf(stderr, "ShmAlloc: alloc of %zu bytes failed\n", size);
    return 1;
  }

  *off = shm_alloc_off;
  shm_alloc_off += size;
  return 0;
}

bool NetPeerAdd(const char *path, bool dev) {
  struct Peer *peer = realloc(peers, sizeof(*peers) * (peer_num + 1));
  if (!peer) {
    perror("NetPeerAdd: realloc failed");
    return false;
  }
  peers = peer;
  peer += peer_num;
  peer_num++;

  if (!(peer->sock_path = strdup(path))) {
    perror("NetPeerAdd: strdup failed");
    return false;
  }
  peer->is_dev = dev;
  peer->sock_fd = -1;
  peer->shm_fd = -1;
  return true;
}


int NetListen() {
#ifdef DEBUG
  fprintf(stderr, "Creating net listening sockets\n");
#endif

  for (size_t i = 0; i < peer_num; i++) {
    struct Peer *peer = &peers[i];
    if (peer->is_dev)
      continue;

#ifdef DEBUG
    fprintf(stderr, "  Creating socket %s %zu\n", peer->sock_path, i);
#endif
    if ((peer->listen_fd = UxsocketInit(peer->sock_path)) < 0) {
      perror("PeersInitNets: unix socket init failed");
      return 1;
    }

    struct epoll_event epev;
    epev.events = EPOLLIN;
    epev.data.ptr = peer;
    if (epoll_ctl(epfd, EPOLL_CTL_ADD, peer->listen_fd, &epev)) {
      perror("PeersInitNets: epoll_ctl accept failed");
      return 1;
    }
  }

#ifdef DEBUG
  fprintf(stderr, "PeerInitNets done\n");
#endif
  return 0;
}

int NetConnect() {
#ifdef DEBUG
  fprintf(stderr, "Connecting to device sockets\n");
#endif

  for (size_t i = 0; i < peer_num; i++) {
    struct Peer *peer = &peers[i];
    if (!peer->is_dev)
      continue;

#ifdef DEBUG
    fprintf(stderr, "  Connecting to socket %s %zu\n", peer->sock_path, i);
#endif

    if ((peer->sock_fd = UxsocketConnect(peer->sock_path)) < 0)
      return 1;

    struct epoll_event epev;
    epev.events = EPOLLIN;
    epev.data.ptr = peer;
    if (epoll_ctl(epfd, EPOLL_CTL_ADD, peer->sock_fd, &epev)) {
      perror("PeersInitNets: epoll_ctl failed");
      return 1;
    }
  }
  return 0;
}

int NetPeerSendDevIntro(struct Peer *peer) {
#ifdef DEBUG
  fprintf(stderr, "PeerDevSendIntro(%s)\n", peer->sock_path);
#endif

  struct SimbricksProtoNetDevIntro *di = &peer->dev_intro;
  peer->local_base = (void *) ((uintptr_t) peer->shm_base + di->d2n_offset);
  peer->local_elen = di->d2n_elen;
  peer->local_enum = di->d2n_nentries;

  peer->cleanup_base = (void *) ((uintptr_t) peer->shm_base + di->n2d_offset);
  peer->cleanup_elen = di->n2d_elen;
  peer->cleanup_enum = di->n2d_nentries;

  struct SimbricksProtoNetNetIntro *ni = &peer->net_intro;
  ssize_t ret = send(peer->sock_fd, ni, sizeof(*ni), 0);
  if (ret < 0) {
    perror("PeerDevSendIntro: send failed");
    return 1;
  } else if (ret != (ssize_t) sizeof(*ni)) {
    fprintf(stderr, "PeerDevSendIntro: send incomplete\n");
    return 1;
  }
  return 0;
}

int NetPeerSetupNetQueues(struct Peer *peer) {
  struct SimbricksProtoNetDevIntro *di = &peer->dev_intro;

#ifdef DEBUG
  fprintf(stderr, "PeerNetSetupQueues(%s)\n", peer->sock_path);
  fprintf(stderr, "  d2n_el=%lu d2n_n=%lu n2d_el=%lu n2d_n=%lu\n", di->d2n_elen,
      di->d2n_nentries, di->n2d_elen, di->n2d_nentries);
#endif

  if (ShmAlloc(di->d2n_elen * di->d2n_nentries, &di->d2n_offset)) {
    fprintf(stderr, "PeerNetSetupQueues: ShmAlloc d2n failed");
    return 1;
  }
  if (ShmAlloc(di->n2d_elen * di->n2d_nentries, &di->n2d_offset)) {
    fprintf(stderr, "PeerNetSetupQueues: ShmAlloc n2d failed");
    return 1;
  }
  peer->shm_fd = shm_fd;
  peer->shm_base = shm_base;

  peer->local_base = (void *) ((uintptr_t) shm_base + di->n2d_offset);
  peer->local_elen = di->n2d_elen;
  peer->local_enum = di->n2d_nentries;

  peer->cleanup_base = (void *) ((uintptr_t) shm_base + di->d2n_offset);
  peer->cleanup_elen = di->d2n_elen;
  peer->cleanup_enum = di->d2n_nentries;

  if (peer->sock_fd == -1) {
    /* We can receive the welcome message from our peer before our local
       connection to the simulator is established. In this case we hold the
       message till the connection is established and send it then. */
#ifdef DEBUG
    fprintf(stderr, "PeerNetSetupQueues: socket not ready yet, delaying "
        "send\n");
#endif
    return 0;
  }

  if (UxsocketSendFd(peer->sock_fd, di, sizeof(*di), peer->shm_fd)) {
    fprintf(stderr, "PeerNetSetupQueues: sending welcome message failed (%lu)",
            peer - peers);
    return 1;
  }
  return 0;
}

int NetPeerReport(struct Peer *peer, uint32_t written_pos, uint32_t clean_pos) {
  if (written_pos == peer->cleanup_pos_last &&
      clean_pos == peer->local_pos_cleaned)
    return 0;

#ifdef DEBUG
  fprintf(stderr, "PeerReport: peer %s written %u -> %u, cleaned %u -> %u\n",
          peer->sock_path, peer->cleanup_pos_last, written_pos,
          peer->local_pos_cleaned, clean_pos);
#endif

  peer->cleanup_pos_last = written_pos;
  while (peer->local_pos_cleaned != clean_pos) {
    void *entry =
        (peer->local_base + peer->local_pos_cleaned * peer->local_elen);
    if (peer->is_dev) {
      struct SimbricksProtoNetD2NDummy *d2n = entry;
      d2n->own_type = SIMBRICKS_PROTO_NET_D2N_OWN_DEV;
    } else {
      struct SimbricksProtoNetN2DDummy *n2d = entry;
      n2d->own_type = SIMBRICKS_PROTO_NET_N2D_OWN_NET;
    }

    peer->local_pos_cleaned += 1;
    if (peer->local_pos_cleaned >= peer->local_enum)
      peer->local_pos_cleaned -= peer->local_enum;
  }

  return 0;
}

static int PeerAcceptEvent(struct Peer *peer) {
#ifdef DEBUG
  fprintf(stderr, "PeerAcceptEvent(%s)\n", peer->sock_path);
#endif
  assert(!peer->is_dev);

  if ((peer->sock_fd = accept(peer->listen_fd, NULL, NULL)) < 0) {
    perror("PeersInitNets: accept failed");
    return 1;
  }

#ifdef DEBUG
  fprintf(stderr, "Accepted %zu\n", peer - peers);
#endif

  close(peer->listen_fd);

  struct epoll_event epev;
  epev.events = EPOLLIN;
  epev.data.ptr = peer;
  if (epoll_ctl(epfd, EPOLL_CTL_ADD, peer->sock_fd, &epev)) {
    perror("PeersInitNets: epoll_ctl failed");
    return 1;
  }

  /* we may have already received the welcome message from our remote peer. In
     that case, send it now. */
  if (peer->intro_valid_remote) {
#ifdef DEBUG
    fprintf(stderr, "PeerAcceptEvent(%s): sending welcome message\n",
        peer->sock_path);
#endif
    if (UxsocketSendFd(peer->sock_fd, &peer->dev_intro, sizeof(peer->dev_intro),
                       peer->shm_fd)) {
      fprintf(stderr, "PeerAcceptEvent: sending welcome message failed (%lu)",
              peer - peers);
      return 1;
    }
  }
  return 0;
}

int NetPeerEvent(struct Peer *peer, uint32_t events) {
#ifdef DEBUG
  fprintf(stderr, "PeerEvent(%s)\n", peer->sock_path);
#endif

  // disable peer if not an input event
  if (!(events & EPOLLIN)) {
    fprintf(stderr, "PeerEvent: non-input event, disabling peer (%s)",
            peer->sock_path);
    peer->ready = false;
    return 1;
  }

  // if peer is network and not yet connected, this is an accept event
  if (!peer->is_dev && peer->sock_fd == -1) {
    return PeerAcceptEvent(peer);
  }

  // if we already have the intro, this is not expected
  if (peer->intro_valid_local) {
    fprintf(stderr, "PeerEvent: receive event after intro (%s)\n",
            peer->sock_path);
    return 1;
  }

  // receive intro message
  if (peer->is_dev) {
    if (UxsocketRecvFd(peer->sock_fd, &peer->dev_intro, sizeof(peer->dev_intro),
                       &peer->shm_fd))
      return 1;

    if (!(peer->shm_base = ShmMap(peer->shm_fd, &peer->shm_size)))
      return 1;
  } else {
    ssize_t ret = recv(peer->sock_fd, &peer->net_intro, sizeof(peer->net_intro),
                       0);
    if (ret < 0) {
      perror("PeerEvent: recv failed");
      return 1;
    } else if (ret != (ssize_t) sizeof(peer->net_intro)) {
      fprintf(stderr, "PeerEvent: partial receive (%zd)\n", ret);
      return 1;
    }
  }

  peer->intro_valid_local = true;

  // pass intro along
  if (NetOpPassIntro(peer))
    return 1;

  if (peer->intro_valid_remote) {
#ifdef DEBUG
    fprintf(stderr, "PeerEvent(%s): marking peer as ready\n", peer->sock_path);
#endif
    peer->ready = true;
  }
  return 0;
}

static inline void PollPeerTransfer(struct Peer *peer, bool *report) {
  // XXX: consider batching this to forward multiple entries at once if possible

  size_t n;
  for (n = 0; n < kPollMax && peer->local_pos + n < peer->local_enum; n++) {
    void *entry = (peer->local_base + (peer->local_pos + n) * peer->local_elen);
    bool ready;
    if (peer->is_dev) {
      struct SimbricksProtoNetD2NDummy *d2n = entry;
      ready = (d2n->own_type & SIMBRICKS_PROTO_NET_D2N_OWN_MASK) ==
          SIMBRICKS_PROTO_NET_D2N_OWN_NET;
    } else {
      struct SimbricksProtoNetN2DDummy *n2d = entry;
      ready = (n2d->own_type & SIMBRICKS_PROTO_NET_N2D_OWN_MASK) ==
          SIMBRICKS_PROTO_NET_N2D_OWN_DEV;
    }
    if (!ready)
      break;
  }

  if (n > 0) {
    NetOpPassEntries(peer, peer->local_pos, n);
    peer->local_pos += n;
    if (peer->local_pos >= peer->local_enum)
      peer->local_pos -= peer->local_enum;

    uint64_t unreported = (peer->local_pos - peer->local_pos_reported) %
                          peer->local_enum;
    if (unreported >= kPollReportThreshold)
      *report = true;
  }
}

static inline void PollPeerCleanup(struct Peer *peer, bool *report) {
  if (peer->cleanup_pos_next == peer->cleanup_pos_last)
    return;

  bool ready;
  uint64_t cnt = 0;
  do {
    void *entry =
        (peer->cleanup_base + peer->cleanup_pos_next * peer->cleanup_elen);
    if (peer->is_dev) {
      struct SimbricksProtoNetN2DDummy *n2d = entry;
      ready = (n2d->own_type & SIMBRICKS_PROTO_NET_N2D_OWN_MASK) ==
          SIMBRICKS_PROTO_NET_N2D_OWN_NET;
    } else {
      struct SimbricksProtoNetD2NDummy *d2n = entry;
      ready = (d2n->own_type & SIMBRICKS_PROTO_NET_D2N_OWN_MASK) ==
          SIMBRICKS_PROTO_NET_D2N_OWN_DEV;
    }

    if (!ready)
      break;

  #ifdef DEBUG
    fprintf(stderr, "PollPeerCleanup: peer %s has clean entry at %u\n",
            peer->sock_path, peer->cleanup_pos_next);
#endif
    peer->cleanup_pos_next += 1;
    if (peer->cleanup_pos_next >= peer->cleanup_enum)
      peer->cleanup_pos_next -= peer->cleanup_enum;
  } while (++cnt <= kCleanupMax &&
           peer->cleanup_pos_next != peer->cleanup_pos_last);

  if (cnt > 0) {
    uint64_t unreported = (peer->cleanup_pos_next - peer->cleanup_pos_reported)
                          % peer->cleanup_enum;
    if (unreported >= kCleanReportThreshold)
      *report = true;
  }
}

void NetPoll() {
  bool report = false;
  for (size_t i = 0; i < peer_num; i++) {
    struct Peer *peer = &peers[i];
    if (!peer->ready)
      continue;

    PollPeerTransfer(peer, &report);
    PollPeerCleanup(peer, &report);
  }

  if (report)
    NetOpPassReport();
}

void NetEntryReceived(struct Peer *peer, uint32_t pos, void *data)
{
  uint64_t off = (uint64_t) pos * peer->cleanup_elen;
  void *entry = peer->cleanup_base + off;

  if (peer->is_dev) {
    struct SimbricksProtoNetD2NDummy *d2n = entry;
    // first copy data after header
    memcpy(d2n + 1, (uint8_t *) data + sizeof(*d2n),
           peer->cleanup_elen - sizeof(*d2n));
    // then copy header except for last byte
    memcpy(entry, data, sizeof(*d2n) - 1);
    // WMB()
    // now copy last byte
    struct SimbricksProtoNetD2NDummy *src_d2n = data;
    d2n->own_type = src_d2n->own_type;
  } else {
    struct SimbricksProtoNetN2DDummy *n2d = entry;
    // first copy data after header
    memcpy(n2d + 1, (uint8_t *) data + sizeof(*n2d),
           peer->cleanup_elen - sizeof(*n2d));
    // then copy header except for last byte
    memcpy(entry, data, sizeof(*n2d) - 1);
    // WMB()
    // now copy last byte
    struct SimbricksProtoNetN2DDummy *src_n2d = data;
    n2d->own_type = src_n2d->own_type;
  }
}