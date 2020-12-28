#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <boost/iostreams/filtering_streambuf.hpp>
#include <boost/iostreams/copy.hpp>
#include <boost/iostreams/filter/gzip.hpp>

#include "events.h"
#include "parser.h"
#include "process.h"

namespace bio = boost::iostreams;

sym_map sym_map;

size_t cpu_lines = 0;
size_t eth_lines = 0;
uint64_t ts_first = 2686011870000ULL;//2655884308815ULL;


void process_msg(uint64_t ts, char *comp_name, size_t comp_name_len, char *msg,
        size_t msg_len)
{
    Event *e = nullptr;
    parser p(msg, msg_len, 0);


    /*if (ts < ts_first)
        return;*/

    if (comp_name_len == 18 && !memcmp(comp_name, "system.switch_cpus", 18)) {
        cpu_lines++;
        if (!p.consume_str("T0 : 0x"))
            return;

        uint64_t addr;
        if (!p.consume_hex(addr) || p.consume_char('.'))
            return;

        if (const std::string *s = sym_map.lookup(addr)) {
            e = new EHostCall(ts, *s);
        }
    } else if (comp_name_len == 18 && !memcmp(comp_name, "system.pc.ethernet", 18)) {
        eth_lines++;

        /*std::cout.write(msg, msg_len);
        std::cout << std::endl;*/

        if (!p.consume_str("cosim: "))
            return;

        uint64_t id = 0;
        uint64_t addr = 0;
        uint64_t size = 0;
        if (p.consume_str("received ")) {
            if (p.consume_str("MSI-X intr vec ") && p.consume_dec(id)) {
                e = new EHostMsiX(ts, id);
            } else if (p.consume_str("DMA read id ") && p.consume_dec(id) &&
                    p.consume_str(" addr ") && p.consume_hex(addr) &&
                    p.consume_str(" size ") && p.consume_dec(size))
            {
                // cosim: received DMA read id 94113551511792 addr 23697ad60 size 20
                e = new EHostDmaR(ts, id, addr, size);
            } else if (p.consume_str("DMA write id ") && p.consume_dec(id) &&
                    p.consume_str(" addr ") && p.consume_hex(addr) &&
                    p.consume_str(" size ") && p.consume_dec(size))
            {
                // cosim: received DMA write id 94113551528032 addr 236972000 size 4
                e = new EHostDmaW(ts, id, addr, size);
            } else if (p.consume_str("read completion id ") &&
                    p.consume_dec(id))
            {
                // cosim: received read completion id 94583743418112
                e = new EHostMmioC(ts, id);
            } else if (p.consume_str("write completion id ") &&
                    p.consume_dec(id))
            {
                // cosim: received write completion id 94583743418736
                e = new EHostMmioC(ts, id);
            }
        } else if (p.consume_str("sending ")) {
            if (p.consume_str("read addr ") && p.consume_hex(addr) &&
                    p.consume_str(" size ") && p.consume_dec(size) &&
                    p.consume_str(" id ") && p.consume_dec(id))
            {
                // cosim: sending read addr c012a500 size 4 id 94583743418112
                e = new EHostMmioR(ts, id, addr, size);
            } else if (p.consume_str("write addr ") && p.consume_hex(addr) &&
                    p.consume_str(" size ") && p.consume_dec(size) &&
                    p.consume_str(" id ") && p.consume_dec(id))
            {
                // cosim: sending write addr c0108000 size 4 id 94584005188256
                e = new EHostMmioW(ts, id, addr, size);
            }
        } else if (p.consume_str("completed DMA id ") && p.consume_dec(id)) {
            e = new EHostDmaC(ts, id);
        }
    }

    if (e) {
        e->dump(std::cout);
    } /*else {
        std::cout.write(msg, msg_len);
        std::cout << std::endl;
    }*/
}

size_t process_line(char *buf, size_t pos, size_t buf_len)
{
    size_t line_start = pos;
    size_t comp_name_start = 0;
    size_t comp_name_len = 0;
    bool valid = true;

    // eat spaces
    for (; pos < buf_len && buf[pos] == ' '; pos++);

    // parse ts
    uint64_t ts = 0;
    size_t ts_len = 0;
    for (; pos < buf_len && buf[pos] >= '0' && buf[pos] <= '9'; pos++) {
        ts = ts * 10 + buf[pos] - '0';
        ts_len++;
    }
    if (ts_len == 0) {
        valid = false;
        goto out;
    }

    // skip colon
    if (buf[pos] != ':') {
        valid = false;
        goto out;
    }
    pos++;

    // skip space
    if (buf[pos] != ' ') {
        valid = false;
        goto out;
    }
    pos++;

    comp_name_start = pos;
    for (; pos < buf_len && buf[pos] != ' ' && buf[pos] != '\n'; pos++, comp_name_len++);
    // skip space
    if (buf[pos] != ' ') {
        valid = false;
        goto out;
    }
    if (buf[pos - 1] != ':') {
        valid = false;
        goto out;
    }
    comp_name_len--;
    pos++;

out:
    // eat line
    size_t msg_start = pos;
    size_t msg_len = 0;
    for (; pos < buf_len && buf[pos] != '\n'; pos++, msg_len++);
    if (pos >= buf_len) {
        // line is incomplete
        return 0;
    }

    buf[pos] = 0;
    if (valid) {
        process_msg(ts, buf + comp_name_start, comp_name_len, buf + msg_start,
                msg_len);
    } else {
        std::cout << buf + line_start << std::endl;
        std::cout << pos << std::endl;
    }

    return pos + 1;
}

void gem5_parse(const std::string &path)
{
    bool use_gz = false;
    std::istream *inf = nullptr;

    if (use_gz) {
        std::ifstream *file = new std::ifstream(path, std::ios_base::in |
                std::ios_base::binary);
        bio::filtering_streambuf<bio::input> *in = new
            bio::filtering_streambuf<bio::input>();

        in->push(bio::gzip_decompressor());
        in->push(*file);

        inf = new std::istream(in);
    } else {
        inf = new std::ifstream(path, std::ios_base::in);
    }

    const size_t buf_size = 16 * 1024 * 1024;
    char *buf = new char[buf_size];

    size_t len, off = 0, pos = 0;

    do {
        inf->read(buf + pos, buf_size - pos);
        len = pos + inf->gcount();
        off += len;

        pos = 0;
        size_t newpos;
        while (pos != len && (newpos = process_line(buf, pos, len)) != 0) {
            pos = newpos;
        }

        if (pos == len) {
            pos = 0;
        } else {
            memmove(buf, buf + pos, len - pos);
            pos = len - pos;
        }
    } while (len > 0);
    delete[] buf;
}

int main(int argc, char *argv[])
{
    sym_map.add_filter("entry_SYSCALL_64");
    sym_map.add_filter("__do_sys_gettimeofday");
    sym_map.add_filter("__sys_sendto");
    sym_map.add_filter("i40e_lan_xmit_frame");
    sym_map.add_filter("syscall_return_via_sysret");
    sym_map.add_filter("__sys_recvfrom");
    sym_map.add_filter("deactivate_task");
    sym_map.add_filter("interrupt_entry");
    sym_map.add_filter("i40e_msix_clean_rings");
    sym_map.add_filter("napi_schedule_prep");
    sym_map.add_filter("__do_softirq");
    sym_map.add_filter("trace_napi_poll");
    sym_map.add_filter("net_rx_action");
    sym_map.add_filter("i40e_napi_poll");
    sym_map.add_filter("activate_task");
    sym_map.add_filter("copyout");

    sym_map.load_file("linux.dump", 0);
    sym_map.load_file("i40e.dump", 0xffffffffa0000000ULL);
    std::cerr << "map loaded" << std::endl;
    gem5_parse(argv[1]);

}
