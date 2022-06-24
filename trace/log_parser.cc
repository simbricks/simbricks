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

#include <boost/iostreams/filter/gzip.hpp>
#include <boost/iostreams/filtering_streambuf.hpp>
#include <fstream>
#include <iostream>

#include "trace/events.h"
#include "trace/parser.h"
#include "trace/process.h"

namespace bio = boost::iostreams;

log_parser::log_parser()
    : inf(nullptr), gz_file(nullptr), gz_in(nullptr), buf_len(0), buf_pos(0) {
  buf = new char[block_size];
}

log_parser::~log_parser() {
  if (inf)
    delete inf;
  if (gz_file) {
    delete gz_in;
    delete gz_file;
  }
  delete[] buf;
}

bool log_parser::next_block() {
  if (buf_pos == buf_len) {
    buf_pos = 0;
  } else {
    memmove(buf, buf + buf_pos, buf_len - buf_pos);
    buf_pos = buf_len - buf_pos;
  }

  inf->read(buf + buf_pos, block_size - buf_pos);
  size_t newlen = inf->gcount();

  buf_len = buf_pos + newlen;
  buf_pos = 0;

  return newlen != 0;
}

void log_parser::open(const char *path) {
  inf = new std::ifstream(path, std::ios_base::in);
}

void log_parser::open_gz(const char *path) {
  gz_file = new std::ifstream(path, std::ios_base::in | std::ios_base::binary);
  gz_in = new bio::filtering_streambuf<bio::input>();

  gz_in->push(bio::gzip_decompressor());
  gz_in->push(*gz_file);

  inf = new std::istream(gz_in);
}

size_t log_parser::try_line() {
  size_t pos = buf_pos;
  size_t line_len = 0;

  for (; pos < buf_len && buf[pos] != '\n'; pos++, line_len++) {
  }
  if (pos >= buf_len) {
    // line is incomplete
    return 0;
  }

  process_line(buf + buf_pos, line_len);

  return pos + 1;
}

bool log_parser::next_event() {
  if (buf_len == 0 && !next_block()) {
    std::cerr << "escape 0" << std::endl;
    return false;
  }

  got_event = false;
  do {
    size_t newpos = try_line();
    if (!newpos) {
      if (!next_block()) {
        std::cerr << "escape 1" << std::endl;
        return false;
      }

      newpos = try_line();
      if (!newpos) {
        std::cerr << "escape 2" << std::endl;
        return false;
      }
    }
    buf_pos = newpos;
  } while (!got_event);

  return true;
}

void log_parser::read_coro(coro_t::push_type &sink_) {
  sink = &sink_;
  while (next_event()) {
  }
}

void log_parser::yield(std::shared_ptr<event> ev) {
  got_event = true;
  ev->source = this;
  (*sink)(ev);
}
