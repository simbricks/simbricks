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

#include "events.h"
#include "parser.h"
#include "process.h"

namespace bio = boost::iostreams;

gem5_parser::gem5_parser(sym_map &syms_)
    : syms(syms_)
{
}

gem5_parser::~gem5_parser()
{
}

void gem5_parser::process_msg(uint64_t ts, char *comp_name,
        size_t comp_name_len, char *msg, size_t msg_len)
{
    parser p(msg, msg_len, 0);

    /*if (ts < ts_first)
        return;*/

    if (comp_name_len == 18 && !memcmp(comp_name, "system.switch_cpus", 18)) {
        //cpu_lines++;
        if (!p.consume_str("T0 : 0x"))
            return;

        uint64_t addr;
        if (!p.consume_hex(addr) || p.consume_char('.'))
            return;

        if (const std::string *s = syms.lookup(addr)) {
            cur_event = new EHostCall(ts, *s);
        }
    } else if (comp_name_len == 18 && !memcmp(comp_name, "system.pc.ethernet", 18)) {
        //eth_lines++;

        /*std::cout.write(msg, msg_len);
        std::cout << std::endl;*/

        if (!p.consume_str("cosim: "))
            return;

        uint64_t id = 0;
        uint64_t addr = 0;
        uint64_t size = 0;
        if (p.consume_str("received ")) {
            if (p.consume_str("MSI-X intr vec ") && p.consume_dec(id)) {
                cur_event = new EHostMsiX(ts, id);
            } else if (p.consume_str("DMA read id ") && p.consume_dec(id) &&
                    p.consume_str(" addr ") && p.consume_hex(addr) &&
                    p.consume_str(" size ") && p.consume_dec(size))
            {
                // cosim: received DMA read id 94113551511792 addr 23697ad60 size 20
                cur_event = new EHostDmaR(ts, id, addr, size);
            } else if (p.consume_str("DMA write id ") && p.consume_dec(id) &&
                    p.consume_str(" addr ") && p.consume_hex(addr) &&
                    p.consume_str(" size ") && p.consume_dec(size))
            {
                // cosim: received DMA write id 94113551528032 addr 236972000 size 4
                cur_event = new EHostDmaW(ts, id, addr, size);
            } else if (p.consume_str("read completion id ") &&
                    p.consume_dec(id))
            {
                // cosim: received read completion id 94583743418112
                cur_event = new EHostMmioC(ts, id);
            } else if (p.consume_str("write completion id ") &&
                    p.consume_dec(id))
            {
                // cosim: received write completion id 94583743418736
                cur_event = new EHostMmioC(ts, id);
            }
        } else if (p.consume_str("sending ")) {
            if (p.consume_str("read addr ") && p.consume_hex(addr) &&
                    p.consume_str(" size ") && p.consume_dec(size) &&
                    p.consume_str(" id ") && p.consume_dec(id))
            {
                // cosim: sending read addr c012a500 size 4 id 94583743418112
                cur_event = new EHostMmioR(ts, id, addr, size);
            } else if (p.consume_str("write addr ") && p.consume_hex(addr) &&
                    p.consume_str(" size ") && p.consume_dec(size) &&
                    p.consume_str(" id ") && p.consume_dec(id))
            {
                // cosim: sending write addr c0108000 size 4 id 94584005188256
                cur_event = new EHostMmioW(ts, id, addr, size);
            }
        } else if (p.consume_str("completed DMA id ") && p.consume_dec(id)) {
            cur_event = new EHostDmaC(ts, id);
        }
    }

    /*if (!cur_event) {
        std::cout.write(msg, msg_len);
        std::cout << std::endl;
    }*/
}


void gem5_parser::process_line(char *line, size_t line_len)
{
    size_t pos = 0;

    size_t line_start = pos;
    size_t comp_name_start = 0;
    size_t comp_name_len = 0;
    bool valid = true;

    // eat spaces
    for (; pos < line_len && line[pos] == ' '; pos++);

    // parse ts
    uint64_t ts = 0;
    size_t ts_len = 0;
    for (; pos < line_len && line[pos] >= '0' && line[pos] <= '9'; pos++) {
        ts = ts * 10 + line[pos] - '0';
        ts_len++;
    }
    if (ts_len == 0) {
        valid = false;
        goto out;
    }

    // skip colon
    if (line[pos] != ':') {
        valid = false;
        goto out;
    }
    pos++;

    // skip space
    if (line[pos] != ' ') {
        valid = false;
        goto out;
    }
    pos++;

    comp_name_start = pos;
    for (; pos < line_len && line[pos] != ' ' && line[pos] != '\n'; pos++,
            comp_name_len++);
    // skip space
    if (line[pos] != ' ') {
        valid = false;
        goto out;
    }
    if (line[pos - 1] != ':') {
        valid = false;
        goto out;
    }
    comp_name_len--;
    pos++;

out:
    size_t msg_start = pos;
    size_t msg_len = line_len - msg_start;
    line[line_len - 1] = 0;
    if (valid) {
        process_msg(ts, line + comp_name_start, comp_name_len, line + msg_start,
                msg_len);
    } else {
        std::cout << line + line_start << std::endl;
        std::cout << pos << std::endl;
    }

    return;
}
