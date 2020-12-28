#pragma once

#include <map>
#include <set>
#include <string>
#include <boost/iostreams/filtering_streambuf.hpp>

#include "events.h"

class sym_map {
  protected:
    bool filter_en;
    bool insmap_en;
    std::set<std::string> filter;

  public:
    std::map<uint64_t, std::string> map;
    std::map<uint64_t, std::string> map_ins;

    void add_filter(const std::string &sym);
    void load_file(const char *path, uint64_t offset = 0);

    inline const std::string *lookup(uint64_t addr)
    {
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
    gem5_parser(sym_map &syms_);
    virtual ~gem5_parser();
};
