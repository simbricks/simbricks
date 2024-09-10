/*
 * Copyright (c) 2024, Carnegie Mellon University
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted (subject to the limitations in the disclaimer
 * below) provided that the following conditions are met:
 *
 *      * Redistributions of source code must retain the above copyright notice,
 *      this list of conditions and the following disclaimer.
 *
 *      * Redistributions in binary form must reproduce the above copyright
 *      notice, this list of conditions and the following disclaimer in the
 *      documentation and/or other materials provided with the distribution.
 *
 *      * Neither the name of the copyright holder nor the names of its
 *      contributors may be used to endorse or promote products derived from
 *      this software without specific prior written permission.
 *
 * NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY
 * THIS LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
 * CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
 * NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
 * PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
 * OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
 * OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
 * ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#pragma once

#include <stdint.h>

namespace enso_bm {
namespace config {

enum config_id {
  FLOW_TABLE_CONFIG_ID = 1,
  TIMESTAMP_CONFIG_ID = 2,
  RATE_LIMIT_CONFIG_ID = 3,
  FALLBACK_QUEUES_CONFIG_ID = 4
};

struct __attribute__((__packed__)) config {
  uint64_t signal;
  uint64_t config_id;
  uint8_t pad[48];
};

struct __attribute__((__packed__)) flow_table {
  uint64_t signal;
  uint64_t config_id;
  uint16_t dst_port;
  uint16_t src_port;
  uint32_t dst_ip;
  uint32_t src_ip;
  uint32_t protocol;
  uint32_t enso_pipe_id;
  uint8_t pad[28];
};

struct __attribute__((__packed__)) timestamp {
  uint64_t signal;
  uint64_t config_id;
  uint64_t enable;
  uint8_t pad[40];
};

struct __attribute__((__packed__)) rate_limit {
  uint64_t signal;
  uint64_t config_id;
  uint16_t denominator;
  uint16_t numerator;
  uint32_t enable;
  uint8_t pad[40];
};

struct __attribute__((__packed__)) fallback_queue {
  uint64_t signal;
  uint64_t config_id;
  uint32_t nb_fallback_queues;
  uint32_t fallback_queue_mask;
  uint64_t enable_rr;
  uint8_t pad[32];
};

}  // namespace config
}  // namespace enso_bm
