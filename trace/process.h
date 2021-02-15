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

#include <boost/iostreams/filtering_streambuf.hpp>
#include <map>
#include <set>
#include <string>

#include "trace/events.h"

class sym_map {
 protected:
  bool filter_en;
  bool insmap_en;
  std::set<std::string> filter;

 public:
  std::map<uint64_t, std::string> map;
  std::map<uint64_t, std::string> map_ins;

  sym_map();

  void add_filter(const std::string &sym);
  void load_file(const char *path, uint64_t offset = 0);

  inline const std::string *lookup(uint64_t addr) {
    auto it = map.find(addr);
    if (it == map.end())
      return nullptr;

    return &it->second;
  }
};

class log_parser {
 protected:
  std::istream *inf;

  std::ifstream *gz_file;
  boost::iostreams::filtering_streambuf<boost::iostreams::input> *gz_in;

  static const size_t block_size = 16 * 1024 * 1024;
  char *buf;
  size_t buf_len;
  size_t buf_pos;

  bool next_block();
  size_t try_line();
  virtual void process_line(char *line, size_t len) = 0;

 public:
  const char *label;
  event *cur_event;

  log_parser();
  virtual ~log_parser();
  void open(const char *path);
  void open_gz(const char *path);

  bool next_event();
};

class gem5_parser : public log_parser {
 protected:
  sym_map &syms;

  virtual void process_line(char *line, size_t len);
  void process_msg(uint64_t ts, char *comp_name, size_t comp_name_len,
                   char *msg, size_t msg_len);

 public:
  explicit gem5_parser(sym_map &syms_);
  virtual ~gem5_parser();
};

class nicbm_parser : public log_parser {
 protected:
  virtual void process_line(char *line, size_t len);

 public:
  virtual ~nicbm_parser();
};
