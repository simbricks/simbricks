#include <iostream>

#include "mem.h"
#include "dma.h"

/*
 * 1024 bits total data width
 * = 128 bytes total
 *
 * 1024 / 8 = 128 bit per segment
 * = 16 bytes / segment
 */

#define DATA_WIDTH (512 * 2)
#define SEG_COUNT 8
#define SEG_WIDTH (DATA_WIDTH / SEG_COUNT)

void MemWriter::step()
{
    if (cur && p.mem_ready) {
        //std::cerr << "completed write to: " << cur->ram_addr << std::endl;
        p.mem_valid = 0;
        p.mem_be[0] = p.mem_be[1] = p.mem_be[2] = p.mem_be[3] = 0;

        if (cur_off == cur->len) {
            /* operation is done */
            pending.pop_front();
            cur->engine->mem_op_complete(cur);
            cur_off = 0;
        } else {
            /* operation is not done yet, we'll pick it back up */
        }
        cur = 0;
    } else if (!cur && !pending.empty()) {
        cur = pending.front();

        //std::cerr << "issuing write to " << cur->ram_addr << std::endl;

        size_t data_byte_width = DATA_WIDTH / 8;
        size_t data_offset = (cur->ram_addr + cur_off) % data_byte_width;

        /*if (cur->len > data_byte_width - data_offset) {
            std::cerr << "MemWriter::step: cannot be written in one cycle TODO" << std::endl;
            throw "unsupported";
        }*/

        /* first reset everything */
        p.mem_sel = 0;
        p.mem_addr[0] = p.mem_addr[1] = p.mem_addr[2] = 0;
        p.mem_be[0] = p.mem_be[1] = p.mem_be[2] = p.mem_be[3] = 0;
        p.mem_valid = 0;


        /* put data bytes in the right places */
        size_t off = data_offset;
        size_t cur_len = (cur->len - cur_off > data_byte_width - data_offset ?
                data_byte_width - data_offset : cur->len - cur_off);
        for (size_t i = 0; i < cur_len; i++, off++) {
            size_t byte_off = off % 4;
            // first clear data byte
            p.mem_data[off / 4] &= ~(0xffu << (byte_off * 8));
            // then set data byte
            p.mem_data[off / 4] |= (((uint32_t) cur->data[i]) << (byte_off * 8));
            p.mem_be[off / 32] |= (1 << (off % 32));
            p.mem_valid |= (1 << (off / (SEG_WIDTH / 8)));
        }

        uint64_t seg_addr = (cur->ram_addr + cur_off) / data_byte_width;
        size_t seg_addr_bits = 12;

        // iterate over the address bit by bit
        for (size_t i = 0; i < seg_addr_bits; i++) {
            uint32_t bit = ((seg_addr >> i) & 0x1);
            // iterate over the segments
            for (size_t j = 0; j < SEG_COUNT; j++) {
                size_t dst_bit = j * seg_addr_bits + i;
                p.mem_addr[dst_bit / 32] |= (bit << (dst_bit % 32));
            }
        }

        cur_off += cur_len;
    }
}

void MemWriter::op_issue(DMAOp *op)
{
    //std::cerr << "enqueued write to " << op->ram_addr << std::endl;
    pending.push_back(op);
}




void MemReader::step()
{
    size_t data_byte_width = DATA_WIDTH / 8;

    if (cur && p.mem_resvalid) {
        std::cerr << "completed read from: " << std::hex << cur->ram_addr << std::endl;
        p.mem_valid = 0;
        /*for (size_t i = 0; i < 32; i++)
            std::cerr << "    val = " << p.mem_data[i] << std::endl;*/
        size_t off = cur->ram_addr % data_byte_width;
        for (size_t i = 0; i < cur->len; i++, off++) {
            size_t byte_off = (off % 4);
            cur->data[i] = (p.mem_data[off / 4] >> (byte_off * 8)) & 0xff;
        }

        if (cur_off == cur->len) {
            /* operation is done */
            pending.pop_front();
            cur->engine->mem_op_complete(cur);
            cur_off = 0;
        } else {
            /* operation is not done yet, we'll pick it back up */
        }

        cur = 0;
    } else if (!cur && !pending.empty()) {
        cur = pending.front();

        std::cerr << "issuing read from " << std::hex << cur->ram_addr << std::endl;

        size_t data_offset = (cur->ram_addr + cur_off) % data_byte_width;
        std::cerr << "    off=" << data_offset << std::endl;

        /*if (cur->len > data_byte_width - data_offset) {
            std::cerr << "MemReader::step: cannot be written in one cycle TODO" << std::endl;
            throw "unsupported";
        }*/

        /* first reset everything */
        p.mem_sel = 0;
        p.mem_addr[0] = p.mem_addr[1] = p.mem_addr[2] = 0;
        p.mem_valid = 0x0;


        /* put data bytes in the right places */
        size_t off = data_offset;
        size_t cur_len = (cur->len - cur_off > data_byte_width - data_offset ?
                data_byte_width - data_offset : cur->len - cur_off);
        for (size_t i = 0; i < cur_len; i++, off++) {
            size_t byte_off = off % 4;
            p.mem_valid |= (1 << (off / (SEG_WIDTH / 8)));
        }
        p.mem_resready = p.mem_valid;

        uint64_t seg_addr = (cur->ram_addr + cur_off) / data_byte_width;
        size_t seg_addr_bits = 12;

        // iterate over the address bit by bit
        for (size_t i = 0; i < seg_addr_bits; i++) {
            uint32_t bit = ((seg_addr >> i) & 0x1);
            // iterate over the segments
            for (size_t j = 0; j < SEG_COUNT; j++) {
                size_t dst_bit = j * seg_addr_bits + i;
                p.mem_addr[dst_bit / 32] |= (bit << (dst_bit % 32));
            }
        }

        /*for (size_t i = 0; i < 3; i++)
            std::cerr << "    addr = " << p.mem_addr[i] << std::endl;
        std::cerr << "    mem_valid = " << (unsigned) p.mem_valid << std::endl;*/

        cur_off += cur_len;
    }
}

void MemReader::op_issue(DMAOp *op)
{
    std::cerr << "enqueued read from " << op->ram_addr << std::endl;
    pending.push_back(op);
}