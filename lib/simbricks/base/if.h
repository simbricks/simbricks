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

#ifndef SIMBRICKS_BASE_IF_H_
#define SIMBRICKS_BASE_IF_H_

#ifdef __cplusplus
// FIXME
#include <simbricks/base/cxxatomicfix.h>
#else
#include <stdatomic.h>
#endif

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#include <simbricks/base/proto.h>

/** Handle for a SHM pool. Treat as opaque. */
struct SimbricksBaseIfSHMPool {
  const char *path;
  int fd;
  void *base;
  size_t size;
  size_t pos;
};

enum SimbricksBaseIfSyncMode {
  /** No synchronization enabled. */
  kSimbricksBaseIfSyncDisabled,
  /** Synchronization enabled if both peers request it. */
  kSimbricksBaseIfSyncOptional,
  /** Enable synchronization and error if not both support it. */
  kSimbricksBaseIfSyncRequired,
};

/** Parameters for a SimBricks interface */
struct SimbricksBaseIfParams {
  /** Link latency/propagation delay [picoseconds] */
  uint64_t link_latency;
  /** Maximum gap between sync messages [picoseconds] */
  uint64_t sync_interval;
  /** Unix socket path to listen on/connect to */
  const char *sock_path;
  /** Synchronization mode: disabled, optional, required */
  enum SimbricksBaseIfSyncMode sync_mode;

  /** for connecters and listeners choose blocking vs. non-blocking. */
  bool blocking_conn;

  /** For listeners: Number of entries in incoming queue*/
  size_t in_num_entries;
  /** For listeners: Size of individual entries in incoming queue */
  size_t in_entries_size;
  /** For listeners: Number of entries in outgoing queue */
  size_t out_num_entries;
  /** For listeners: Size of individual entries in outgoing queue */
  size_t out_entries_size;

  uint64_t upper_layer_proto;
};

/** Handle for a SimBricks base interface. Treat as opaque. */
struct SimbricksBaseIf {
  void *in_queue;
  size_t in_pos;
  size_t in_elen;
  size_t in_enum;
  uint64_t in_timestamp;

  void *out_queue;
  size_t out_pos;
  size_t out_elen;
  size_t out_enum;
  uint64_t out_timestamp;

  int conn_state;
  int sync;
  struct SimbricksBaseIfParams params;
  struct SimbricksBaseIfSHMPool *shm;
  int listen_fd;
  int conn_fd;
  bool listener;
};


/** Create and map a new shared memory pool with the specified path and size. */
int SimbricksBaseIfSHMPoolCreate(struct SimbricksBaseIfSHMPool *pool,
                                 const char *path, size_t pool_size);
/** Map existing shared memory pool by file descriptor. */
int SimbricksBaseIfSHMPoolMapFd(struct SimbricksBaseIfSHMPool *pool,
                                int fd);
/** Map existing shared memory pool by path. */
int SimbricksBaseIfSHMPoolMap(struct SimbricksBaseIfSHMPool *pool,
                              const char *path);
/** Unmap shared memory pool, without unlinking it. */
int SimbricksBaseIfSHMPoolUnmap(struct SimbricksBaseIfSHMPool *pool);
/** Delete but don't unmap shared memory pool. */
int SimbricksBaseIfSHMPoolUnlink(struct SimbricksBaseIfSHMPool *pool);


/** Initialize params struct with default values */
void SimbricksBaseIfDefaultParams(struct SimbricksBaseIfParams *params);

/** Required SHM size for these parameters */
size_t SimbricksBaseIfSHMSize(struct SimbricksBaseIfParams *params);

int SimbricksBaseIfInit(struct SimbricksBaseIf *base_if,
                        struct SimbricksBaseIfParams *params);

/** Create listening base interface. Note this does not wait for a connector. */
int SimbricksBaseIfListen(struct SimbricksBaseIf *base_if,
                          struct SimbricksBaseIfSHMPool *pool);
/** Initiate connection for base interface. Note this is asynchronous. */
int SimbricksBaseIfConnect(struct SimbricksBaseIf *base_if);
/** Check if incoming/outgoing connection is established . (non-blocking) */
int SimbricksBaseIfConnected(struct SimbricksBaseIf *base_if);
/** FD to wait on for listen or connect event. */
int SimbricksBaseIfConnFd(struct SimbricksBaseIf *base_if);
/** Block till base_if is connected or failed */
int SimbricksBaseIfConnsWait(struct SimbricksBaseIf **base_ifs, unsigned n);

/** Send intro. */
int SimbricksBaseIfIntroSend(struct SimbricksBaseIf *base_if,
                             const void *payload, size_t payload_len);
/** Receive intro. */
int SimbricksBaseIfIntroRecv(struct SimbricksBaseIf *base_if,
                             void *payload, size_t *payload_len);
/** FD to wait on for intro events. */
int SimbricksBaseIfIntroFd(struct SimbricksBaseIf *base_if);


void SimbricksBaseIfClose(struct SimbricksBaseIf *base_if);
void SimbricksBaseIfUnlink(struct SimbricksBaseIf *base_if);

/**
 * Poll for an incoming message without advancing the position if one is found.
 * Message must be retrieved again with a call to `SimbricksBaseIfInPoll`
 *
 * @param base_if   Base interface handle (connected).
 * @param timestamp Current timestamp (in picoseconds).
 * @return Pointer to the message struct if successfull, NULL otherwise.
 */
static inline volatile union SimbricksProtoBaseMsg *SimbricksBaseIfInPeek(
    struct SimbricksBaseIf *base_if,
    uint64_t timestamp) {
  volatile union SimbricksProtoBaseMsg *msg =
      (volatile union SimbricksProtoBaseMsg *) (void *) (
        (uint8_t *) base_if->in_queue + base_if->in_pos * base_if->in_elen);
  uint8_t own_type = atomic_load_explicit(
      (volatile _Atomic(uint8_t) *) &msg->header.own_type,
      memory_order_acquire);

  /* message not ready */
  if ((own_type & SIMBRICKS_PROTO_MSG_OWN_MASK) !=
      SIMBRICKS_PROTO_MSG_OWN_CON)
    return NULL;

  /* if in sync mode, wait till message is ready */
  base_if->in_timestamp = msg->header.timestamp;
  if (base_if->sync && base_if->in_timestamp > timestamp)
    return NULL;

  return msg;
}

/**
 * Poll for an incoming message. After processing the message must be freed by
 * calling `SimbricksBaseIfInDone`.
 *
 * @param base_if   Base interface handle (connected).
 * @param timestamp Current timestamp (in picoseconds).
 * @return Pointer to the message struct if successfull, NULL otherwise.
 */
static inline volatile union SimbricksProtoBaseMsg *SimbricksBaseIfInPoll(
    struct SimbricksBaseIf *base_if,
    uint64_t timestamp) {
  volatile union SimbricksProtoBaseMsg *msg =
      SimbricksBaseIfInPeek(base_if, timestamp);

  if (msg != NULL)
    base_if->in_pos = (base_if->in_pos + 1) % base_if->in_enum;
  return msg;
}

/**
 * Read message type from received message.
 *
 * @param base_if  Base interface handle (connected).
 * @param msg      Pointer to the previously received message.
 */
static inline uint8_t SimbricksBaseIfInType(
    struct SimbricksBaseIf *base_if,
    volatile union SimbricksProtoBaseMsg *msg) {
  return (msg->header.own_type & ~SIMBRICKS_PROTO_MSG_OWN_MASK);

}

/**
 * Mark received message as processed and pass ownership of the slot back to the
 * sender.
 *
 * @param base_if  Base interface handle (connected).
 * @param msg      Pointer to the previously received message.
 */
static inline void SimbricksBaseIfInDone(
    struct SimbricksBaseIf *base_if,
    volatile union SimbricksProtoBaseMsg *msg) {
  atomic_store_explicit(
      (volatile _Atomic(uint8_t) *) &msg->header.own_type,
      (uint8_t) ((msg->header.own_type & ~SIMBRICKS_PROTO_MSG_OWN_MASK) |
        SIMBRICKS_PROTO_MSG_OWN_PRO),
      memory_order_release);
}

/**
 * Message timestamp of the next. Valid only after a poll failed because of a
 * future timestamp.
 *
 * @param base_if Base interface handle (connected).
 * @return Input timestamp.
 */
static inline uint64_t SimbricksBaseIfInTimestamp(
    struct SimbricksBaseIf *base_if) {
  return base_if->in_timestamp;
}

/**
 * Allocate a new message in the queue. Must be followed by a call to
 * `SimbricksBaseIfOutSend`.
 *
 * @param base_if   Base interface handle (connected).
 * @param timestamp Current timestamp (in picoseconds).
 * @return Pointer to the message struct if successfull, NULL otherwise.
 */
static inline volatile union SimbricksProtoBaseMsg *SimbricksBaseIfOutAlloc(
    struct SimbricksBaseIf *base_if,
    uint64_t timestamp) {
  volatile union SimbricksProtoBaseMsg *msg =
      (volatile union SimbricksProtoBaseMsg *) (void *) (
        (uint8_t *) base_if->out_queue + base_if->out_pos * base_if->out_elen);

  uint8_t own_type = atomic_load_explicit(
      (volatile _Atomic(uint8_t) *) &msg->header.own_type,
      memory_order_acquire);
  if ((own_type & SIMBRICKS_PROTO_MSG_OWN_MASK) !=
      SIMBRICKS_PROTO_MSG_OWN_PRO) {
    return NULL;
  }

  msg->header.timestamp = timestamp + base_if->params.link_latency;
  base_if->out_timestamp = timestamp;

  base_if->out_pos = (base_if->out_pos + 1) % base_if->out_enum;
  return msg;  
}

/**
 * Send out a fully filled message. Sets the message type and ownership flag.
 * Also acts as a compiler barrier to avoid other writes to the message being
 * reordered after this.
 *
 * @param base_if  Base interface handle (connected).
 * @param msg      Pointer to the previously allocated and fully initialized
                   message (other than the type.).
 * @param msg_type Message type to set (without ownership flag).
 */
static inline void SimbricksBaseIfOutSend(
    struct SimbricksBaseIf *base_if, volatile union SimbricksProtoBaseMsg *msg,
    uint8_t msg_type) {
  atomic_store_explicit((volatile _Atomic(uint8_t) *) &msg->header.own_type,
                        (uint8_t) (msg_type | SIMBRICKS_PROTO_MSG_OWN_CON),
                        memory_order_release);
}

/**
 * Send a synchronization dummy message if necessary.
 *
 * @param base_if   Base interface handle (connected).
 * @param timestamp Current timestamp (in picoseconds).
 * @return 0 if sync successfully sent, 1 if sync was unnecessary, -1 if a
 * necessary sync message could not be sent because the queue is full.
 */
static inline int SimbricksBaseIfOutSync(struct SimbricksBaseIf *base_if,
                                         uint64_t timestamp) {
  if (!base_if->sync || (base_if->out_timestamp > 0 &&
                         timestamp - base_if->out_timestamp <
                         base_if->params.sync_interval))
    return 0;

  volatile union SimbricksProtoBaseMsg *msg =
      SimbricksBaseIfOutAlloc(base_if, timestamp);
  if (!msg)
    return -1;

  SimbricksBaseIfOutSend(base_if, msg, SIMBRICKS_PROTO_MSG_TYPE_SYNC);
  return 0;  
}

/**
 * Timestamp when the next sync or data packet must be sent.
 *
 * @param base_if   Base interface handle (connected).
 * @return Timestamp. Undefined if synchronization is disabled.
 */
static inline uint64_t SimbricksBaseIfOutNextSync(
    struct SimbricksBaseIf *base_if)
{
  return base_if->out_timestamp + base_if->params.sync_interval;
}

/**
 * Retrieve maximal total message length for outgoing messages.
 * 
 * @param base_if Base interface handle (connected).
 * @return Maximal message length in bytes.
 */
static inline size_t SimbricksBaseIfOutMsgLen(struct SimbricksBaseIf *base_if) {
  return base_if->out_elen;
}

/**
 * Check if synchronization is enabled for this connection.
 *
 * @param base_if Base interface handle (connected).
 * @return true if synchronized, false otherwise.
 */
static inline bool SimbricksBaseIfSyncEnabled(struct SimbricksBaseIf *base_if) {
  return base_if->sync;
}

#endif  // SIMBRICKS_BASEIF_BASEIF_H_
