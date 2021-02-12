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

#include <fstream>

#include "trace/parser.h"
#include "trace/process.h"

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
