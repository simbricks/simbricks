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

#pragma once

#include <cstddef>
#include <cstring>
#include <string>

class parser {
 protected:
  const char *buf;
  size_t buf_len;
  size_t pos;

 public:
  parser(const char *buf_, size_t buf_len_, size_t start_pos = 0)
      : buf(buf_), buf_len(buf_len_), pos(start_pos) {
  }

  inline size_t trim_spaces() {
    size_t cnt = 0;
    for (; pos < buf_len && buf[pos] == ' '; pos++, cnt++) {
    }
    return cnt;
  }

  inline bool consume_char(char c) {
    if (pos == buf_len || buf[pos] != c) {
      return false;
    }

    pos++;
    return true;
  }

  inline bool consume_hex(uint64_t &val) {
    size_t val_len = 0;
    val = 0;
    for (; pos < buf_len; pos++) {
      char d = buf[pos];
      bool is_d = d >= '0' && d <= '9';
      bool is_x = d >= 'a' && d <= 'f';

      if (!is_d && !is_x)
        break;

      val <<= 4;
      if (is_d)
        val |= d - '0';
      else
        val |= d - 'a' + 10;
      val_len++;
    }

    return val_len > 0;
  }

  inline bool consume_dec(uint64_t &val) {
    size_t val_len = 0;
    val = 0;
    for (; pos < buf_len; pos++) {
      char d = buf[pos];
      if (d < '0' || d > '9')
        break;

      val = val * 10 + (d - '0');
      val_len++;
    }

    return val_len > 0;
  }

  inline bool consume_str(const char *str) {
    size_t str_len = strlen(str);
    if (pos + str_len > buf_len || memcmp(buf + pos, str, str_len)) {
      return false;
    }

    pos += str_len;
    return true;
  }

  inline bool extract_until(char end_c, std::string &str) {
    size_t end = pos;
    for (; end < buf_len && buf[end] != end_c; end++) {
    }

    if (end >= buf_len)
      return false;

    str.assign(buf + pos, end - pos);
    pos = end + 1;
    return true;
  }
};
