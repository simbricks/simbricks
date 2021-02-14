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

#ifndef SIMBRICKS_PROTO_NETWORK_H_
#define SIMBRICKS_PROTO_NETWORK_H_

#include <stdint.h>

/******************************************************************************/
/* Initialization messages on Unix socket */

/** in dev_intro.flags to indicate that sender supports issuing syncs. */
#define SIMBRICKS_PROTO_NET_FLAGS_DI_SYNC (1 << 0)

/**
 * welcome message sent by device to network. This message comes with the shared
 * memory file descriptor attached.
 */
struct SimbricksProtoNetDevIntro {
  /** flags: see SIMBRICKS_PROTO_NET_FLAGS_DI_* */
  uint64_t flags;

  /** offset of the device-to-network queue in shared memory region */
  uint64_t d2n_offset;
  /** size of an entry in the device-to-network queue in bytes */
  uint64_t d2n_elen;
  /** total device-to-network queue length in #entries */
  uint64_t d2n_nentries;

  /** offset of the net-to-device queue in shared memory region */
  uint64_t n2d_offset;
  /** size of an entry in the net-to-device queue in bytes */
  uint64_t n2d_elen;
  /** total net-to-device queue length in #entries */
  uint64_t n2d_nentries;
} __attribute__((packed));

#define SIMBRICKS_PROTO_NET_FLAGS_NI_SYNC (1 << 0)

/** welcome message sent by network to device */
struct SimbricksProtoNetNetIntro {
  /** flags: see SIMBRICKS_PROTO_NET_FLAGS_IN_* */
  uint64_t flags;
} __attribute__((packed));

/******************************************************************************/
/* Messages on in-memory device to network channel */

/** Mask for ownership bit in own_type field */
#define SIMBRICKS_PROTO_NET_D2N_OWN_MASK 0x80
/** Message is owned by device */
#define SIMBRICKS_PROTO_NET_D2N_OWN_DEV 0x00
/** Message is owned by network */
#define SIMBRICKS_PROTO_NET_D2N_OWN_NET 0x80

/** Mask for type value in own_type field */
#define SIMBRICKS_PROTO_NET_D2N_MSG_MASK 0x7f
#define SIMBRICKS_PROTO_NET_D2N_MSG_SYNC 0x1
#define SIMBRICKS_PROTO_NET_D2N_MSG_SEND 0x2

struct SimbricksProtoNetD2NDummy {
  uint8_t pad[48];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));

struct SimbricksProtoNetD2NSync {
  uint8_t pad[48];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));

struct SimbricksProtoNetD2NSend {
  uint16_t len;
  uint8_t port;
  uint8_t pad[45];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
  uint8_t data[];
} __attribute__((packed));

union SimbricksProtoNetD2N {
  struct SimbricksProtoNetD2NDummy dummy;
  struct SimbricksProtoNetD2NSync sync;
  struct SimbricksProtoNetD2NSend send;
};

/******************************************************************************/
/* Messages on in-memory network to device channel */

#define SIMBRICKS_PROTO_NET_N2D_OWN_MASK 0x80
/** Message is owned by host */
#define SIMBRICKS_PROTO_NET_N2D_OWN_NET 0x00
/** Message is owned by device */
#define SIMBRICKS_PROTO_NET_N2D_OWN_DEV 0x80

#define SIMBRICKS_PROTO_NET_N2D_MSG_MASK 0x7f
#define SIMBRICKS_PROTO_NET_N2D_MSG_SYNC 0x1
#define SIMBRICKS_PROTO_NET_N2D_MSG_RECV 0x2

struct SimbricksProtoNetN2DDummy {
  uint8_t pad[48];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));

struct SimbricksProtoNetN2DSync {
  uint8_t pad[48];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));

struct SimbricksProtoNetN2DRecv {
  uint16_t len;
  uint8_t port;
  uint8_t pad[45];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
  uint8_t data[];
};

union SimbricksProtoNetN2D {
  struct SimbricksProtoNetN2DDummy dummy;
  struct SimbricksProtoNetN2DSync sync;
  struct SimbricksProtoNetN2DRecv recv;
};

#endif  // SIMBRICKS_PROTO_NETWORK_H_
