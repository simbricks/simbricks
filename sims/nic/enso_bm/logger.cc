/*
 * Copyright (c) 2021-2024, Max Planck Institute for Software Systems,
 * National University of Singapore, and Carnegie Mellon University
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

#include <iostream>

#include "sims/nic/enso_bm/enso_bm.h"

namespace enso_bm {

logger::logger(const std::string &label_, nicbm::Runner::Device &dev_)
    : label(label_), dev(dev_), runner(dev_.runner_) {
  ss << std::hex;
}

logger &logger::operator<<(char c) {
  if (c == endl) {
    uint64_t ts;

    /* runner might not be initialized yet if called from a constructor
     * somewhere, in that case see if it's set now otherwise just take 0 as the
     * current timestamp. */
    if (!runner) {
      runner = dev.runner_;
      ts = runner ? runner->TimePs() : 0;
    } else {
      ts = runner->TimePs();
    }

    std::cerr << ts << " " << label << ": " << ss.str() << std::endl;
    ss.str(std::string());
    ss << std::hex;
  } else {
    ss << c;
  }
  return *this;
}

logger &logger::operator<<(int32_t i) {
  ss << i;
  return *this;
}

logger &logger::operator<<(uint8_t i) {
  ss << (unsigned)i;
  return *this;
}

logger &logger::operator<<(uint16_t i) {
  ss << i;
  return *this;
}

logger &logger::operator<<(uint32_t i) {
  ss << i;
  return *this;
}

logger &logger::operator<<(uint64_t i) {
  ss << i;
  return *this;
}

logger &logger::operator<<(bool b) {
  ss << b;
  return *this;
}

logger &logger::operator<<(const char *str) {
  ss << str;
  return *this;
}

logger &logger::operator<<(void *ptr) {
  ss << ptr;
  return *this;
}
}  // namespace enso_bm
