/*
 * Copyright (c) 2021-2024, Max Planck Institute for Software Systems,
 * National University of Singapore, and Carnegie Mellon University
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

#include <cstdint>
#include <iostream>

namespace enso_bm {

struct four_tuple {
  uint16_t dst_port;
  uint16_t src_port;
  uint32_t dst_ip;
  uint32_t src_ip;

  bool operator==(const four_tuple &other) const {
    return dst_port == other.dst_port && src_port == other.src_port &&
           dst_ip == other.dst_ip && src_ip == other.src_ip;
  }
};

class logger : public std::ostream {
 public:
  static const char endl = '\n';

 protected:
  std::string label;
  nicbm::Runner::Device &dev;
  nicbm::Runner *runner;
  std::stringstream ss;

 public:
  explicit logger(const std::string &label_, nicbm::Runner::Device &dev_);
  logger &operator<<(char c);
  logger &operator<<(int32_t c);
  logger &operator<<(uint8_t i);
  logger &operator<<(uint16_t i);
  logger &operator<<(uint32_t i);
  logger &operator<<(uint64_t i);
  logger &operator<<(bool c);
  logger &operator<<(const char *str);
  logger &operator<<(void *str);
};

}  // namespace enso_bm

template <>
struct std::hash<struct enso_bm::four_tuple> {
  std::size_t operator()(const struct enso_bm::four_tuple &s) const noexcept {
    std::size_t h1 = std::hash<uint16_t>{}(s.dst_port);
    std::size_t h2 = std::hash<uint16_t>{}(s.src_port);
    std::size_t h3 = std::hash<uint32_t>{}(s.dst_ip);
    std::size_t h4 = std::hash<uint32_t>{}(s.src_ip);
    return h1 ^ (h2 << 1) ^ (h3 << 2) ^ (h4 << 3);
  }
};

constexpr uint16_t le_to_be_16(const uint16_t be) {
  return ((be & (uint16_t)0x00ff) << 8) | ((be & (uint16_t)0xff00) >> 8);
}

constexpr uint32_t le_to_be_32(const uint32_t be) {
  return ((be & (uint32_t)0x000000ff) << 24) |
         ((be & (uint32_t)0x0000ff00) << 8) |
         ((be & (uint32_t)0x00ff0000) >> 8) |
         ((be & (uint32_t)0xff000000) >> 24);
}

constexpr uint16_t be_to_le_16(const uint16_t le) {
  return le_to_be_16(le);
}

constexpr uint32_t be_to_le_32(const uint32_t le) {
  return le_to_be_32(le);
}
