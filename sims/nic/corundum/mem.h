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

#ifndef DMA_H_
#define DMA_H_

#include <deque>

#include "Vinterface.h"
#include "verilated.h"

class DMAOp;

struct MemReadPort {
   /* outputs to memory */
    vluint8_t   &mem_sel;
    vluint32_t (&mem_addr)[3];
    vluint8_t   &mem_valid;
    vluint8_t   &mem_resready;

    /* inputs from memory */
    vluint32_t (&mem_data)[32];
    vluint8_t   &mem_ready;
    vluint8_t   &mem_resvalid; /* for read only */

    MemReadPort(vluint8_t &mem_sel_, vluint32_t (&mem_addr_)[3],
            vluint8_t &mem_valid_, vluint8_t &mem_resready_,
            vluint32_t (&mem_data_)[32], vluint8_t &mem_ready_,
            vluint8_t &mem_resvalid_)
        : mem_sel(mem_sel_), mem_addr(mem_addr_), mem_valid(mem_valid_),
        mem_resready(mem_resready_), mem_data(mem_data_), mem_ready(mem_ready_),
        mem_resvalid(mem_resvalid_)
    {
    }
};

struct MemWritePort {
    /* outputs to memory */
    vluint8_t   &mem_sel;
    vluint32_t (&mem_be)[4]; /* for write only */
    vluint32_t (&mem_addr)[3];
    vluint32_t (&mem_data)[32];
    vluint8_t   &mem_valid;

    /* inputs from memory */
    vluint8_t   &mem_ready;

    MemWritePort(vluint8_t &mem_sel_, vluint32_t (&mem_be_)[4],
            vluint32_t (&mem_addr_)[3], vluint32_t (&mem_data_)[32],
            vluint8_t &mem_valid_, vluint8_t &mem_ready_)
        : mem_sel(mem_sel_), mem_be(mem_be_), mem_addr(mem_addr_),
        mem_data(mem_data_), mem_valid(mem_valid_), mem_ready(mem_ready_)
    {
    }
};

class MemReader {
    protected:
        MemReadPort &p;

        std::deque<DMAOp *> pending;
        DMAOp *cur;
        size_t cur_off;

    public:
        MemReader(MemReadPort &p_)
            : p(p_), cur(0), cur_off(0)
        {
        }

        void step();
        void op_issue(DMAOp *op);
};

class MemWriter {
    protected:
        MemWritePort &p;

        std::deque<DMAOp *> pending;
        DMAOp *cur;
        size_t cur_off;

    public:
        MemWriter(MemWritePort &p_)
            : p(p_), cur(0), cur_off(0)
        {
        }

        void step();
        void op_issue(DMAOp *op);
};

#endif /* ndef MEM_H_ */
