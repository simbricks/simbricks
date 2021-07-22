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

#include <iostream>

#include "trace/events.h"
#include "trace/parser.h"
#include "trace/process.h"

namespace bio = boost::iostreams;

nicbm_parser::~nicbm_parser() {
}

void nicbm_parser::process_line(char *line, size_t line_len) {
  parser p(line, line_len, 0);

  uint64_t ts;
  if (!p.consume_dec(ts))
    return;

  if (!p.consume_str(" nicbm: "))
    return;

  uint64_t id, addr, len, val;
  if (p.consume_str("read(off=0x")) {
    if (p.consume_hex(addr) && p.consume_str(", len=") && p.consume_dec(len) &&
        p.consume_str(", val=0x") && p.consume_hex(val)) {
      yield(std::make_shared<e_nic_mmio_r>(ts, addr, len, val));
    }
  } else if (p.consume_str("write(off=0x")) {
    if (p.consume_hex(addr) && p.consume_str(", len=") && p.consume_dec(len) &&
        p.consume_str(", val=0x") && p.consume_hex(val)) {
      yield(std::make_shared<e_nic_mmio_w>(ts, addr, len, val));
    }
  } else if (p.consume_str("issuing dma op 0x")) {
    if (p.consume_hex(id) && p.consume_str(" addr ") && p.consume_hex(addr) &&
        p.consume_str(" len ") && p.consume_hex(len)) {
      yield(std::make_shared<e_nic_dma_i>(ts, id, addr, len));
    }
  } else if (p.consume_str("completed dma read op 0x") ||
             p.consume_str("completed dma write op 0x")) {
    if (p.consume_hex(id) && p.consume_str(" addr ") && p.consume_hex(addr) &&
        p.consume_str(" len ") && p.consume_hex(len)) {
      yield(std::make_shared<e_nic_dma_c>(ts, id));
    }
  } else if (p.consume_str("issue MSI-X interrupt vec ")) {
    if (p.consume_dec(id)) {
      yield(std::make_shared<e_nic_msix>(ts, id));
    }
  } else if (p.consume_str("eth tx: len ")) {
    if (p.consume_dec(len)) {
      yield(std::make_shared<e_nic_tx>(ts, len));
    }
  } else if (p.consume_str("eth rx: port 0 len ")) {
    if (p.consume_dec(len)) {
      yield(std::make_shared<e_nic_rx>(ts, len));
    }
#if 1
  }
#else
  } else {
    std::cerr.write(line, line_len);
    std::cerr << std::endl;
  }
#endif
}
