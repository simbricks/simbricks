#ifndef MEM_H_
#define MEM_H_

#include <set>
#include <deque>

#include "Vinterface.h"
#include "verilated.h"

#define MAX_DMA_LEN 2048

class DMAEngine;
class MemWriter;
class MemReader;

struct DMAPorts {
    /* inputs to DMA engine */
    vluint64_t &dma_addr;
    vluint8_t  &dma_ram_sel;
    vluint32_t &dma_ram_addr;
    vluint16_t &dma_len;
    vluint8_t  &dma_tag;
    vluint8_t  &dma_valid;

    /* outputs of DMA engine */
    vluint8_t &dma_ready;
    vluint8_t &dma_status_tag;
    vluint8_t &dma_status_valid;


    DMAPorts(vluint64_t &dma_addr_, vluint8_t &dma_ram_sel_,
            vluint32_t &dma_ram_addr_, vluint16_t &dma_len_,
            vluint8_t &dma_tag_, vluint8_t &dma_valid_,
            vluint8_t &dma_ready_, vluint8_t &dma_status_tag_,
            vluint8_t &dma_status_valid_)
        : dma_addr(dma_addr_), dma_ram_sel(dma_ram_sel_),
        dma_ram_addr(dma_ram_addr_), dma_len(dma_len_),
        dma_tag(dma_tag_), dma_valid(dma_valid_),
        dma_ready(dma_ready_), dma_status_tag(dma_status_tag_),
        dma_status_valid(dma_status_valid_)
    {
    }
};

struct DMAOp {
    DMAEngine *engine;
    uint64_t dma_addr;
    size_t len;
    uint64_t ram_addr;
    bool write;
    uint8_t  ram_sel;
    uint8_t tag;
    uint8_t data[MAX_DMA_LEN];
};

class DMAEngine {
    protected:
        DMAPorts &p;

        DMAEngine(DMAPorts &p_)
            : p(p_) { }

    public:
        virtual void pci_op_complete(DMAOp *op) = 0;
        virtual void mem_op_complete(DMAOp *op) = 0;
};

class DMAReader : public DMAEngine {
    protected:
        std::set<DMAOp *> pending;
        std::deque<DMAOp *> completed;
        const char *label;
        MemWriter &mw;

    public:
        DMAReader(const char *label_, DMAPorts &p_, MemWriter &mw_)
            : DMAEngine(p_), label(label_), mw(mw_)
        {
        }

        virtual void pci_op_complete(DMAOp *op);
        virtual void mem_op_complete(DMAOp *op);
        void step();
};

class DMAWriter : public DMAEngine {
    protected:
        std::set<DMAOp *> pending;
        std::deque<DMAOp *> completed;
        const char *label;
        MemReader &mr;

    public:
        DMAWriter(const char *label_, DMAPorts &p_, MemReader &mr_)
            : DMAEngine(p_), label(label_), mr(mr_)
        {
        }

        virtual void pci_op_complete(DMAOp *op);
        virtual void mem_op_complete(DMAOp *op);
        void step();
};


#endif /* ndef DMA_H_ */
