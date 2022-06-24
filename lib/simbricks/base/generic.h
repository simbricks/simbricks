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

#ifndef SIMBRICKS_BASE_GENERIC_H_
#define SIMBRICKS_BASE_GENERIC_H_

#include <simbricks/base/if.h>

/**
 * Generates static inline functions specialized for message types of a specific
 * SimBricks protocol. These are thin wrappers around the baseif functions but
 * insert appropriate casts.
 *
 * Generates the following function with the specified prefix:
 *  - In: prefixInPeek (wraps `SimbricksBaseIfInPeek`)
 *  - In: prefixInPoll (wraps `SimbricksBaseIfInPoll`)
 *  - In: prefixInType (wraps `SimbricksBaseIfInType`)
 *  - In: prefixInDone (wraps `SimbricksBaseIfInDone`)
 *  - In: prefixInTimestamp (wraps `SimbricksBaseIfInTimestamp`)
 *  - Out: prefixOutAlloc (wraps `SimbricksBaseIfOutAlloc`)
 *  - Out: prefixOutSend (wraps `SimbricksBaseIfOutSend`)
 *  - Out: prefixOutSync (wraps `SimbricksBaseIfOutSync`)
 *  - Out: prefixOutNextSync (wraps `SimbricksBaseIfOutNextSync`)
 *  - Out: prefixOutMsgLen (wraps `SimBricksBaseIfOutMsgLen`)
 *
 * @param prefix    Name prefix for all the functions
 * @param msg_union Union name for the message type of the protocol. (not
 *                  including the "union" keyword).
 * @param if_struct Interfacing struct, (member base must be
 *                  `struct SimBricksBaseIf`).
 */
#define SIMBRICKS_BASEIF_GENERIC(prefix, msg_union, if_struct)                 \
                                                                               \
  static inline volatile union msg_union *prefix##InPeek(                      \
      struct if_struct *base_if, uint64_t ts) {                                \
    return (volatile union msg_union *)SimbricksBaseIfInPeek(&base_if->base,   \
                                                             ts);              \
  }                                                                            \
                                                                               \
  static inline volatile union msg_union *prefix##InPoll(                      \
      struct if_struct *base_if, uint64_t ts) {                                \
    return (volatile union msg_union *)SimbricksBaseIfInPoll(&base_if->base,   \
                                                             ts);              \
  }                                                                            \
                                                                               \
  static inline uint8_t prefix##InType(struct if_struct *base_if,              \
                                       volatile union msg_union *msg) {        \
    return SimbricksBaseIfInType(&base_if->base, &msg->base);                  \
  }                                                                            \
                                                                               \
  static inline void prefix##InDone(struct if_struct *base_if,                 \
                                    volatile union msg_union *msg) {           \
    SimbricksBaseIfInDone(&base_if->base, &msg->base);                         \
  }                                                                            \
                                                                               \
  static inline uint64_t prefix##InTimestamp(struct if_struct *base_if) {      \
    return SimbricksBaseIfInTimestamp(&base_if->base);                         \
  }                                                                            \
                                                                               \
  static inline volatile union msg_union *prefix##OutAlloc(                    \
      struct if_struct *base_if, uint64_t timestamp) {                         \
    return (volatile union msg_union *)SimbricksBaseIfOutAlloc(&base_if->base, \
                                                               timestamp);     \
  }                                                                            \
                                                                               \
  static inline void prefix##OutSend(struct if_struct *base_if,                \
                                     volatile union msg_union *msg,            \
                                     uint8_t msg_type) {                       \
    SimbricksBaseIfOutSend(&base_if->base, &msg->base, msg_type);              \
  }                                                                            \
                                                                               \
  static inline int prefix##OutSync(struct if_struct *base_if,                 \
                                    uint64_t timestamp) {                      \
    return SimbricksBaseIfOutSync(&base_if->base, timestamp);                  \
  }                                                                            \
                                                                               \
  static inline uint64_t prefix##OutNextSync(struct if_struct *base_if) {      \
    return SimbricksBaseIfOutNextSync(&base_if->base);                         \
  }                                                                            \
                                                                               \
  static inline size_t prefix##OutMsgLen(struct if_struct *base_if) {          \
    return SimbricksBaseIfOutMsgLen(&base_if->base);                           \
  }

#endif  // SIMBRICKS_BASE_GENERIC_H_
