#include <iostream>

#include "debug.h"
#include "corundum.h"
#include "dma.h"
#include "mem.h"


void DMAReader::step()
{
    p.dma_ready = 1;
    if (p.dma_valid) {
        DMAOp *op = new DMAOp;
        op->engine = this;
        op->dma_addr = p.dma_addr;
        op->ram_sel = p.dma_ram_sel;
        op->ram_addr = p.dma_ram_addr;
        op->len = p.dma_len;
        op->tag = p.dma_tag;
        op->write = false;
        pending.insert(op);

#ifdef DMA_DEBUG
        std::cout << main_time << " dma[" << label << "] op " << std::hex << op->dma_addr << " -> " <<
            op->ram_sel << ":" << op->ram_addr <<
            "   len=" << op->len << "   tag=" << (int) op->tag << std::endl;
#endif

        coord.dma_register(op, true);
    }

    p.dma_status_valid = 0;
    if (!completed.empty()) {
        DMAOp *op = completed.front();
        completed.pop_front();

        //std::cout << "dma[" << label << "] status complete " << op->dma_addr << std::endl;

        p.dma_status_valid = 1;
        p.dma_status_tag = op->tag;
        pending.erase(op);
        delete op;
    }
}

void DMAReader::pci_op_complete(DMAOp *op)
{
    mw.op_issue(op);
}

void DMAReader::mem_op_complete(DMAOp *op)
{
    completed.push_back(op);
    //std::cout << "dma[" << label << "] mem complete " << op->dma_addr << std::endl;
}



void DMAWriter::step()
{
    p.dma_ready = 1;
    if (p.dma_valid) {
        DMAOp *op = new DMAOp;
        op->engine = this;
        op->dma_addr = p.dma_addr;
        op->ram_sel = p.dma_ram_sel;
        op->ram_addr = p.dma_ram_addr;
        op->len = p.dma_len;
        op->tag = p.dma_tag;
        op->write = true;
        pending.insert(op);

#ifdef DMA_DEBUG
        std::cout << main_time << " dma write [" << label << "] op " << std::hex << op->dma_addr << " -> " <<
            op->ram_sel << ":" << op->ram_addr <<
            "   len=" << op->len << "   tag=" << (int) op->tag << std::endl;
#endif

        coord.dma_register(op, false);
        mr.op_issue(op);
    }

    p.dma_status_valid = 0;
    if (!completed.empty()) {
        DMAOp *op = completed.front();
        completed.pop_front();

#ifdef DMA_DEBUG
        std::cout << main_time << " dma write [" << label << "] status complete " << op->dma_addr << std::endl;
#endif

        p.dma_status_valid = 1;
        p.dma_status_tag = op->tag;
        pending.erase(op);
        //coord.msi_enqueue(0);
        delete op;
    }
}

void DMAWriter::pci_op_complete(DMAOp *op)
{
#ifdef DMA_DEBUG
    std::cout << main_time << " dma write [" << label << "] pci complete " << op->dma_addr << std::endl;
#endif
    completed.push_back(op);
}

void DMAWriter::mem_op_complete(DMAOp *op)
{
#ifdef DMA_DEBUG
    std::cout << main_time << " dma write [" << label << "] mem complete " << op->dma_addr << ": ";
    for (size_t i = 0; i < op->len; i++)
        std::cout << (unsigned) op->data[i] << " ";
    std::cout << std::endl;
#endif
    coord.dma_mark_ready(op);
}
