#pragma once

#include <map>
#include <set>
#include <string>

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
