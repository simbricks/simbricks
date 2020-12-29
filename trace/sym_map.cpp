#include <fstream>

#include "parser.h"
#include "process.h"


sym_map::sym_map()
    : filter_en(false), insmap_en(false)
{
}

void sym_map::add_filter(const std::string &sym)
{
    filter_en = true;
    filter.insert(sym);
}

void sym_map::load_file(const char *path, uint64_t offset)
{
    std::ifstream file(path, std::ios_base::in | std::ios_base::binary);
    std::string line;
    std::string label = "";

    while (std::getline(file, line)) {
        parser p(line.c_str(), line.size());
        uint64_t addr;

        p.trim_spaces();
        p.consume_hex(addr);

        if (p.consume_char(':')) {
            if (insmap_en && !label.empty()) {
                map_ins[addr + offset] = label;
            }
        } else if (p.consume_str(" <")) {
            p.extract_until('>', label);

            if (!filter_en || filter.find(label) != filter.end())
                map[addr + offset] = label;
        }
    }
}
