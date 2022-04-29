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

#include "dist/common/base.h"

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

#include <simbricks/base/proto.h>

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

int BaseInit(const char *shm_path_, size_t shm_size_, int epfd_) {
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

bool BasePeerAdd(const char *path, bool listener) {
  struct Peer *peer = realloc(peers, sizeof(*peers) * (peer_num + 1));
  if (!peer) {
    perror("NetPeerAdd: realloc failed");
    return false;
  }
  peers = peer;
  peer += peer_num;
  peer_num++;

  memset(peer, 0, sizeof(*peer));
  if (!(peer->sock_path = strdup(path))) {
    perror("NetPeerAdd: strdup failed");
    return false;
  }
  peer->is_listener = listener;
  peer->sock_fd = -1;
  peer->shm_fd = -1;
  peer->last_sent_pos = -1;
  return true;
}


int BaseListen() {
#ifdef DEBUG
  fprintf(stderr, "Creating listening sockets\n");
#endif

  for (size_t i = 0; i < peer_num; i++) {
    struct Peer *peer = &peers[i];
    if (!peer->is_listener)
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

int BaseConnect() {
#ifdef DEBUG
  fprintf(stderr, "Connecting to device sockets\n");
#endif

  for (size_t i = 0; i < peer_num; i++) {
    struct Peer *peer = &peers[i];
    if (peer->is_listener)
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

int BasePeerSetupQueues(struct Peer *peer) {
  if (!peer->is_listener) {
    /* only need to set up queues for listeners */
    return 0;
  }

  struct SimbricksProtoListenerIntro *li =
      (struct SimbricksProtoListenerIntro *) peer->intro_remote;

#ifdef DEBUG
  fprintf(stderr, "PeerNetSetupQueues(%s)\n", peer->sock_path);
  fprintf(stderr, "  l2c_el=%lu l2c_n=%lu c2l_el=%lu c2l_n=%lu\n", li->l2c_elen,
      li->l2c_nentries, li->c2l_elen, li->c2l_nentries);
#endif

  if (ShmAlloc(li->l2c_elen * li->l2c_nentries, &li->l2c_offset)) {
    fprintf(stderr, "PeerNetSetupQueues: ShmAlloc l2c failed");
    return 1;
  }
  if (ShmAlloc(li->c2l_elen * li->c2l_nentries, &li->c2l_offset)) {
    fprintf(stderr, "PeerNetSetupQueues: ShmAlloc c2l failed");
    return 1;
  }
  peer->shm_fd = shm_fd;
  peer->shm_base = shm_base;

  peer->local_base = (void *) ((uintptr_t) shm_base + li->c2l_offset);
  peer->local_elen = li->c2l_elen;
  peer->local_enum = li->c2l_nentries;

  peer->cleanup_base = (void *) ((uintptr_t) shm_base + li->l2c_offset);
  peer->cleanup_elen = li->l2c_elen;
  peer->cleanup_enum = li->l2c_nentries;

  return 0;
}

int BasePeerSendIntro(struct Peer *peer) {
#ifdef DEBUG
  fprintf(stderr, "PeerDevSendIntro(%s)\n", peer->sock_path);
#endif

 if (peer->sock_fd == -1) {
    /* We can receive the welcome message from our peer before our local
       connection to the simulator is established. In this case we hold the
       message till the connection is established and send it then. */
#ifdef DEBUG
    fprintf(stderr, "PeerNetSetupQueues: socket not ready yet, delaying "
        "send\n");
#endif
    return 1;
  }

  int shm_fd = (peer->is_listener ? peer->shm_fd : -1);
  if (UxsocketSendFd(peer->sock_fd, peer->intro_remote, peer->intro_remote_len,
      shm_fd)) {
    perror("BasePeerSendIntro: send failed");
    return 1;
  }
  return 0;
}

int BasePeerReport(struct Peer *peer, uint32_t written_pos, uint32_t clean_pos) {
  uint32_t pos = peer->local_pos_cleaned;
  if (written_pos == peer->cleanup_pos_last &&
      clean_pos == pos)
    return 0;

  // make sure there are not suddenly fewer entries to be cleaned up
  uint32_t n_before = (peer->cleanup_pos_reported <= peer->cleanup_pos_last ?
      peer->cleanup_pos_last - peer->cleanup_pos_reported :
      peer->cleanup_enum - peer->cleanup_pos_reported + peer->cleanup_pos_last);
  uint32_t n_after = (peer->cleanup_pos_reported <= written_pos ?
      written_pos - peer->cleanup_pos_reported :
      peer->cleanup_enum - peer->cleanup_pos_reported + written_pos);
  if (n_before > n_after) {
    fprintf(stderr, "PeerReport: BUG fewer entries to clean up after report: "
          "peer %s written %u -> %u, cleaned %u -> %u\n",
          peer->sock_path, peer->cleanup_pos_last, written_pos,
          peer->local_pos_cleaned, clean_pos);
    abort();
  }

  // make sure clean pos is between l_p_c and l_p_r
  if (((peer->local_pos_cleaned <= peer->local_pos_reported) &&
          (clean_pos < peer->local_pos_cleaned ||
            clean_pos > peer->local_pos_reported)) ||
      ((peer->local_pos_cleaned > peer->local_pos_reported) &&
          (clean_pos > peer->local_pos_reported &&
           clean_pos < peer->local_pos_cleaned))) {
    fprintf(stderr, "PeerReport: BUG invalid last clean position report: "
          "peer %s written %u -> %u, cleaned %u -> %u (lpr=%u)\n",
          peer->sock_path, peer->cleanup_pos_last, written_pos,
          peer->local_pos_cleaned, clean_pos, peer->local_pos_reported);
    abort();
  }

#ifdef DEBUG
  fprintf(stderr, "PeerReport: peer %s written %u -> %u, cleaned %u -> %u\n",
          peer->sock_path, peer->cleanup_pos_last, written_pos,
          peer->local_pos_cleaned, clean_pos);
#endif

  peer->cleanup_pos_last = written_pos;
  while (pos != clean_pos) {
    void *entry = (peer->local_base + pos * peer->local_elen);
    volatile union SimbricksProtoBaseMsg *msg =
        (volatile union SimbricksProtoBaseMsg *) entry;
      msg->header.own_type = (msg->header.own_type &
          (~SIMBRICKS_PROTO_MSG_OWN_MASK)) | SIMBRICKS_PROTO_MSG_OWN_PRO;

    pos += 1;
    if (pos >= peer->local_enum)
      pos -= peer->local_enum;
  }
  peer->local_pos_cleaned = pos;

  return 0;
}

static int PeerAcceptEvent(struct Peer *peer) {
#ifdef DEBUG
  fprintf(stderr, "PeerAcceptEvent(%s)\n", peer->sock_path);
#endif
  assert(peer->is_listener);

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
    if (BasePeerSendIntro(peer)) {
      fprintf(stderr, "PeerAcceptEvent(%s): sending intro failed\n",
          peer->sock_path);
      return 1;
    }
  }
  return 0;
}

int BasePeerEvent(struct Peer *peer, uint32_t events) {
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
  if (peer->is_listener && peer->sock_fd == -1) {
    return PeerAcceptEvent(peer);
  }

  // if we already have the intro, this is not expected
  if (peer->intro_valid_local) {
    fprintf(stderr, "PeerEvent: receive event after intro (%s)\n",
            peer->sock_path);
    return 1;
  }

  // receive intro message
  if (!peer->is_listener) {
    /* not a listener, so we're expecting an fd for the shm region */
    if (UxsocketRecvFd(peer->sock_fd, peer->intro_local,
        sizeof(peer->intro_local), &peer->shm_fd))
      return 1;

    if (!(peer->shm_base = ShmMap(peer->shm_fd, &peer->shm_size)))
      return 1;
  } else {
    /* as a listener, we use our local shm region, so no fd is sent to us */
    ssize_t ret = recv(peer->sock_fd, peer->intro_local,
        sizeof(peer->intro_local), 0);
    if (ret <= 0) {
      perror("PeerEvent: recv failed");
      return 1;
    }
  }

  peer->intro_valid_local = true;

  // pass intro along
  if (BaseOpPassIntro(peer))
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

  uint32_t n;
  for (n = 0; n < kPollMax && peer->local_pos + n < peer->local_enum; n++) {
    // stop if we would pass the cleanup position
    if ((peer->local_pos + n + 1) % peer->local_enum ==
        peer->local_pos_cleaned) {
#ifdef DEBUG
      fprintf(stderr, "PollPeerTransfer: waiting for cleanup (%u %u)\n",
              pos, peer->local_pos_cleaned);
#endif
      break;
    }

    void *entry = (peer->local_base + (peer->local_pos + n) * peer->local_elen);
    volatile union SimbricksProtoBaseMsg *msg =
        (volatile union SimbricksProtoBaseMsg *) entry;
    if ((msg->header.own_type & SIMBRICKS_PROTO_MSG_OWN_MASK) !=
        SIMBRICKS_PROTO_MSG_OWN_CON)
      break;
  }

  if (n > 0) {
    BaseOpPassEntries(peer, peer->local_pos, n);
    uint32_t newpos = peer->local_pos + n;
    peer->local_pos = (newpos < peer->local_enum ?
                       newpos :
                       newpos - peer->local_enum);

    uint64_t unreported = (peer->local_pos - peer->local_pos_reported) %
                          peer->local_enum;
    if (unreported >= kPollReportThreshold)
      *report = true;
  }
}

static inline void PollPeerCleanup(struct Peer *peer, bool *report) {
  if (peer->cleanup_pos_next == peer->cleanup_pos_last)
    return;

  uint64_t cnt = 0;
  do {
    void *entry =
        (peer->cleanup_base + peer->cleanup_pos_next * peer->cleanup_elen);
    volatile union SimbricksProtoBaseMsg *msg =
        (volatile union SimbricksProtoBaseMsg *) entry;

    if ((msg->header.own_type & SIMBRICKS_PROTO_MSG_OWN_MASK) !=
        SIMBRICKS_PROTO_MSG_OWN_PRO)
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

void BasePoll() {
  bool report = false;
  for (size_t i = 0; i < peer_num; i++) {
    struct Peer *peer = &peers[i];
    if (!peer->ready)
      continue;

    PollPeerTransfer(peer, &report);
    PollPeerCleanup(peer, &report);
  }

  if (report)
    BaseOpPassReport();
}

void BaseEntryReceived(struct Peer *peer, uint32_t pos, void *data)
{
  // validate position for debugging:
  if ((peer->cleanup_pos_reported <= peer->cleanup_pos_last &&
        (pos >= peer->cleanup_pos_reported && pos < peer->cleanup_pos_last)) ||
      (peer->cleanup_pos_reported > peer->cleanup_pos_last &&
        (pos >= peer->cleanup_pos_reported ||
         pos < peer->cleanup_pos_last))) {
    fprintf(stderr, "NetEntryReceived: BUG position %u is in window to be "
            "cleaned %u -> %u", pos, peer->cleanup_pos_reported,
            peer->cleanup_pos_last);
    abort();
  }

  uint64_t off = (uint64_t) pos * peer->cleanup_elen;
  void *entry = peer->cleanup_base + off;
  volatile union SimbricksProtoBaseMsg *msg =
        (volatile union SimbricksProtoBaseMsg *) entry;
  
  // first copy data after header
  memcpy((void *) (msg + 1), (uint8_t *) data + sizeof(*msg),
          peer->cleanup_elen - sizeof(*msg));
  // then copy header except for last byte
  memcpy((void *) msg, data, sizeof(*msg) - 1);
  // WMB()
  // now copy last byte
  volatile union SimbricksProtoBaseMsg *src_msg =
        (volatile union SimbricksProtoBaseMsg *) data;
  asm volatile("sfence" ::: "memory");
  msg->header.own_type = src_msg->header.own_type;
}