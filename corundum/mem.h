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
