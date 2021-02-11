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

#include "i40e_bm.h"

using namespace i40e;

rss_key_cache::rss_key_cache(const uint32_t (&key_)[key_len / 4])
    : key(key_)
{
    cache_dirty = true;
}


void rss_key_cache::build()
{
    const uint8_t *k = reinterpret_cast<const uint8_t *> (&key);
    uint32_t result = (((uint32_t)k[0]) << 24) |
        (((uint32_t)k[1]) << 16) |
        (((uint32_t)k[2]) << 8) |
        ((uint32_t)k[3]);

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

void rss_key_cache::set_dirty()
{
    cache_dirty = true;
}

uint32_t rss_key_cache::hash_ipv4(uint32_t sip, uint32_t dip, uint16_t sp,
        uint16_t dp)
{
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
            res ^= cache[32+i];
        dip <<= 1;
    }
    for (i = 0; i < 16; i++) {
        if (sp & MSB16)
            res ^= cache[64+i];
        sp <<= 1;
    }
    for (i = 0; i < 16; i++) {
        if (dp & MSB16)
            res ^= cache[80+i];
        dp <<= 1;
    }

    return res;
}

#if 0
int main(int argc, char *argv[])
{
    static const uint8_t key[] = {
            0x6d, 0x5a, 0x56, 0xda, 0x25, 0x5b, 0x0e, 0xc2,
            0x41, 0x67, 0x25, 0x3d, 0x43, 0xa3, 0x8f, 0xb0,
            0xd0, 0xca, 0x2b, 0xcb, 0xae, 0x7b, 0x30, 0xb4,
            0x77, 0xcb, 0x2d, 0xa3, 0x80, 0x30, 0xf2, 0x0c,
            0x6a, 0x42, 0xb7, 0x3b, 0xbe, 0xac, 0x01, 0xfa,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
    };

    uint32_t kregs[13];

    key_cache kc(kregs);
    memcpy(kregs, key, sizeof(key));
    kc.set_dirty();


    printf("%x\n", kc.hash_ipv4(0x420995bb, 0xa18e6450, 2794, 1766));
    printf("%x\n", kc.hash_ipv4(0x420995bb, 0xa18e6450, 0, 0));
    return 0;
}
#endif
