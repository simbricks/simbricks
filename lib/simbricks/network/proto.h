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

#ifndef SIMBRICKS_NETWORK_PROTO_H_
#define SIMBRICKS_NETWORK_PROTO_H_

#include <stdint.h>

#include <simbricks/base/proto.h>

/******************************************************************************/
/* Initialization messages on Unix socket */

/** welcome message sent by network devices to eachother. */
struct SimbricksProtoNetIntro {
  uint32_t dummy; /* not used, but need to avoid empty struct for standard C */
} __attribute__((packed));

/******************************************************************************/
/* The network protocol is symmetric */

/** a network packet */
#define SIMBRICKS_PROTO_NET_MSG_PACKET 0x40

struct SimbricksProtoNetMsgPacket {
  uint16_t len;
  uint8_t port;
  uint8_t pad[45];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
  uint8_t data[];
} __attribute__((packed));

union SimbricksProtoNetMsg {
  union SimbricksProtoBaseMsg base;
  struct SimbricksProtoNetMsgPacket packet;
};

#endif  // SIMBRICKS_NETWORK_PROTO_H_
