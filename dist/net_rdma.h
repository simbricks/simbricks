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

#ifndef DIST_NET_RDMA_NET_RDMA_H_
#define DIST_NET_RDMA_NET_RDMA_H_

#include <arpa/inet.h>
#include <stdbool.h>
#include <stddef.h>

#include <simbricks/proto/network.h>

struct Peer {
  /* base address of the local queue we're polling.
     (d2n or n2d depending on is_dev). */
  uint8_t *local_base;
  uint32_t local_elen;
  uint32_t local_enum;
  uint32_t local_pos;
  // last position reported to our peer
  uint32_t local_pos_reported;
  // last position cleaned
  uint32_t local_pos_cleaned;

  // rkey and base address of the remote queue to write to
  uint64_t remote_rkey;
  uint64_t remote_base;

  /* For cleanup we poll the queue just to see when entries get freed. We need
     to know up to where we can poll, i.e. what entries the peer has written to.
     The peer communicates this position periodically and we store it in
     `cleanup_pos_last`. `cleanup_pos_next` refers to the next entry we will
     poll. Finally we need to report the freed positions to our peer again, so
     the peer can mark these entries as unused in it's local queue, we again do
     this periodically and keep track of the last communicated position in
     `cleanup_pos_reported`. */
  uint8_t *cleanup_base;
  uint32_t cleanup_elen;
  uint32_t cleanup_enum;
  // next position to be cleaned up
  uint32_t cleanup_pos_next;
  // first entry not ready for cleanup yet
  volatile uint32_t cleanup_pos_last;
  // last cleanup position reported to peer
  uint32_t cleanup_pos_reported;


  struct SimbricksProtoNetDevIntro dev_intro;
  struct SimbricksProtoNetNetIntro net_intro;
  const char *sock_path;

  /* RDMA memory region for the shared memory of the queues on this end. Could
     be either our own global SHM region if this is a network peer, or the SHM
     region allocated by the device peer. */
  struct ibv_mr *shm_mr;
  void *shm_base;
  size_t shm_size;

  int sock_fd;
  int shm_fd;

  // is our local peer a device? (otherwise it's a network)
  bool is_dev;

  bool intro_valid_local;
  bool intro_valid_remote;

  // set true when the queue is ready for polling
  volatile bool ready;
};

// configuration variables
extern bool mode_listen;
extern const char *shm_path;
extern size_t shm_size;
extern void *shm_base;
extern size_t peer_num;
extern struct Peer *peers;
extern int epfd;

int PeerDevSendIntro(struct Peer *peer);
int PeerNetSetupQueues(struct Peer *peer);
int PeerReport(struct Peer *peer, uint32_t written_pos, uint32_t clean_pos);

int RdmaListen(struct sockaddr_in *addr);
int RdmaConnect(struct sockaddr_in *addr);
int RdmaPassIntro(struct Peer *peer);
int RdmaPassEntry(struct Peer *peer);
int RdmaPassReport();
int RdmaEvent();

#endif  // DIST_NET_RDMA_NET_RDMA_H_