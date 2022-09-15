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

#ifndef SIMBRICKS_BASE_PROTO_H_
#define SIMBRICKS_BASE_PROTO_H_

#include <assert.h>
#include <stdint.h>

#define SIMBRICKS_PROTO_MSG_SZCHECK(s) \
  static_assert(sizeof(s) == 64, "SimBrick message size check failed")

#define SIMBRICKS_PROTO_VERSION 1

#define SIMBRICKS_PROTO_ID_BASE 0x00
#define SIMBRICKS_PROTO_ID_NET 0x01
#define SIMBRICKS_PROTO_ID_PCIE 0x02
#define SIMBRICKS_PROTO_ID_MEM 0x03

/** Listener requests synchronization */
#define SIMBRICKS_PROTO_FLAGS_LI_SYNC (1 << 0)
/** Listener forces synchronization */
#define SIMBRICKS_PROTO_FLAGS_LI_SYNC_FORCE (1 << 1)

/**
 * Welcome message that the listener sends to the connector on the unix socket.
 * The message specifies if and what synchronization is enabled, the shared
 * memory queues information, and information on the upper layer protocol. The
 * message on the Unix socket also includes the shared memory file descriptor
 * with this message. Finally the intro also contains the upper-layer intro.
 */
struct SimbricksProtoListenerIntro {
  /** simbricks protocol version */
  uint64_t version;

  /** flags: see SIMBRICKS_PROTO_FLAGS_LI_* */
  uint64_t flags;

  /** offset of the listener-to-connecter queue in shared memory region */
  uint64_t l2c_offset;
  /** size of an entry in the listener-to-connecter queue in bytes */
  uint64_t l2c_elen;
  /** total listener-to-connecter queue length in #entries */
  uint64_t l2c_nentries;

  /** offset of the connecter-to-listener queue in shared memory region */
  uint64_t c2l_offset;
  /** size of an entry in the host-to-device queue in bytes */
  uint64_t c2l_elen;
  /** total host-to-device queue length in #entries */
  uint64_t c2l_nentries;

  /** upper layer protocol identifier: see SIMBRICKS_PROTO_ID_* */
  uint64_t upper_layer_proto;
  /** offset of upper layer intro from beginning of this message */
  uint64_t upper_layer_intro_off;
} __attribute__((packed));

/** Connecter has synchronization enabled */
#define SIMBRICKS_PROTO_FLAGS_CO_SYNC (1 << 0)
/** Connecter forces synchronization */
#define SIMBRICKS_PROTO_FLAGS_CO_SYNC_FORCE (1 << 1)

struct SimbricksProtoConnecterIntro {
  /** simbricks protocol version */
  uint64_t version;

  /** flags: see SIMBRICKS_PROTO_FLAGS_CO_* */
  uint64_t flags;

  /** upper layer protocol identifier: see SIMBRICKS_PROTO_ID_* */
  uint64_t upper_layer_proto;
  /** offset of upper layer intro from beginning of this message */
  uint64_t upper_layer_intro_off;
} __attribute__((packed));

/** Mask for ownership bit in own_type field */
#define SIMBRICKS_PROTO_MSG_OWN_MASK 0x80
/** Message is owned by producer */
#define SIMBRICKS_PROTO_MSG_OWN_PRO 0x00
/** Message is owned by consumer */
#define SIMBRICKS_PROTO_MSG_OWN_CON 0x80

/** Mask for messsage type in own_type field */
#define SIMBRICKS_PROTO_MSG_TYPE_MASK 0x7f

/** Pure Sync Message, no upper layer data */
#define SIMBRICKS_PROTO_MSG_TYPE_SYNC 0x00
/** Peer Termination Message, no upper layer data */
#define SIMBRICKS_PROTO_MSG_TYPE_TERMINATE 0x01
/* values in between are reserved for future extensions */
/** first message type reserved for upper layer protocols */
#define SIMBRICKS_PROTO_MSG_TYPE_UPPER_START 0x40

struct SimbricksProtoBaseMsgHeader {
  uint8_t pad[48];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoBaseMsgHeader);

union SimbricksProtoBaseMsg {
  struct SimbricksProtoBaseMsgHeader header;
  struct SimbricksProtoBaseMsgHeader sync;
  struct SimbricksProtoBaseMsgHeader terminate;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(union SimbricksProtoBaseMsg);

/* deprecated */
#define SIMBRICKS_PROTO_SYNC_SIMBRICKS 0
#define SIMBRICKS_PROTO_SYNC_BARRIER 1

#endif  // SIMBRICKS_BASE_PROTO_H_
