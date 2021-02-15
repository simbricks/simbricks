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

#include "sims/nic/i40e_bm/i40e_bm.h"

namespace i40e {

rss_key_cache::rss_key_cache(const uint32_t (&key_)[key_len / 4]) : key(key_) {
  cache_dirty = true;
}

void rss_key_cache::build() {
  const uint8_t *k = reinterpret_cast<const uint8_t *>(&key);
  uint32_t result = (((uint32_t)k[0]) << 24) | (((uint32_t)k[1]) << 16) |
                    (((uint32_t)k[2]) << 8) | ((uint32_t)k[3]);

  uint32_t idx = 32;
  size_t i;

  for (i = 0; i < cache_len; i++, idx++) {
    uint8_t shift = (idx % 8);
    uint32_t bit;

    cache[i] = result;
    bit = ((k[idx / 8] << shift) & 0x80) ? 1 : 0;
    result = ((result << 1) | bit);
  }

  cache_dirty = false;
}

void rss_key_cache::set_dirty() {
  cache_dirty = true;
}

uint32_t rss_key_cache::hash_ipv4(uint32_t sip, uint32_t dip, uint16_t sp,
                                  uint16_t dp) {
  static const uint32_t MSB32 = 0x80000000;
  static const uint32_t MSB16 = 0x8000;
  uint32_t res = 0;
  int i;

  if (cache_dirty)
    build();

  for (i = 0; i < 32; i++) {
    if (sip & MSB32)
      res ^= cache[i];
    sip <<= 1;
  }
  for (i = 0; i < 32; i++) {
    if (dip & MSB32)
      res ^= cache[32 + i];
    dip <<= 1;
  }
  for (i = 0; i < 16; i++) {
    if (sp & MSB16)
      res ^= cache[64 + i];
    sp <<= 1;
  }
  for (i = 0; i < 16; i++) {
    if (dp & MSB16)
      res ^= cache[80 + i];
    dp <<= 1;
  }

  return res;
}
}  // namespace i40e
