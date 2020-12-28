#include <iostream>

#include "events.h"
#include "parser.h"
#include "process.h"

namespace bio = boost::iostreams;

nicbm_parser::~nicbm_parser()
{
}

void nicbm_parser::process_line(char *line, size_t line_len)
{
    parser p(line, line_len, 0);

    uint64_t ts;
    if (!p.consume_dec(ts))
        return;

    if (!p.consume_str(" nicbm: "))
        return;

    uint64_t id, addr, len, val;
    if (p.consume_str("read(off=0x")) {
        if (p.consume_hex(addr) &&
            p.consume_str(", len=") &&
            p.consume_dec(len) &&
            p.consume_str(", val=0x") &&
            p.consume_hex(val))
        {
            cur_event = new e_nic_mmio_r(ts, addr, len, val);
        }
    } else if (p.consume_str("write(off=0x")) {
        if (p.consume_hex(addr) &&
            p.consume_str(", len=") &&
            p.consume_dec(len) &&
            p.consume_str(", val=0x") &&
            p.consume_hex(val))
        {
            cur_event = new e_nic_mmio_w(ts, addr, len, val);
        }
    } else if (p.consume_str("issuing dma op 0x")) {
        if (p.consume_hex(id) &&
            p.consume_str(" addr ") &&
            p.consume_hex(addr) &&
            p.consume_str(" len ") &&
            p.consume_hex(len))
        {
            cur_event = new e_nic_dma_i(ts, id, addr, len);
        }
    } else if (p.consume_str("completed dma read op 0x")  ||
            p.consume_str("completed dma write op 0x"))
    {
        if (p.consume_hex(id) &&
            p.consume_str(" addr ") &&
            p.consume_hex(addr) &&
            p.consume_str(" len ") &&
            p.consume_hex(len))
        {
            cur_event = new e_nic_dma_c(ts, id);
        }
    } else if (p.consume_str("issue MSI-X interrupt vec ")) {
        if (p.consume_dec(id)) {
            cur_event = new e_nic_msix(ts, id);
        }
    } else if (p.consume_str("eth tx: len ")) {
        if (p.consume_dec(len)) {
            cur_event = new e_nic_tx(ts, len);
        }
    } else if (p.consume_str("eth rx: port 0 len ")) {
        if (p.consume_dec(len)) {
            cur_event = new e_nic_rx(ts, len);
        }
    }/* else {
        std::cerr.write(line, line_len);
        std::cerr << std::endl;
    }*/
}
