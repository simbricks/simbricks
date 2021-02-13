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

#ifndef COORD_H_
#define COORD_H_

#include <deque>
#include <iostream>
#include <map>

#include "sims/nic/corundum/debug.h"

class DMAOp;
struct MMIOOp;

void pci_dma_issue(DMAOp *op);
void pci_msi_issue(uint8_t vec);
void pci_rwcomp_issue(MMIOOp *op);

class PCICoordinator {
 protected:
  struct PCIOp {
    union {
      DMAOp *dma_op;
      MMIOOp *mmio_op;
      uint32_t msi_vec;
    };
    enum {
      OP_DMA,
      OP_MSI,
      OP_RWCOMP,
    } type;
    bool ready;
  };

  std::deque<PCIOp *> queue;
  std::map<DMAOp *, PCIOp *> dmamap;

  void process() {
    PCIOp *op;
    while (!queue.empty()) {
      op = queue.front();
      if (!op->ready)
        break;

      queue.pop_front();
      if (op->type == PCIOp::OP_MSI) {
#ifdef COORD_DEBUG
        std::cout << main_time << " issuing msi " << op->msi_vec << std::endl;
#endif
        pci_msi_issue(op->msi_vec);
      } else if (op->type == PCIOp::OP_DMA) {
#ifdef COORD_DEBUG
        std::cout << main_time << " issuing dma " << op->dma_op << std::endl;
#endif
        pci_dma_issue(op->dma_op);
        dmamap.erase(op->dma_op);
      } else if (op->type == PCIOp::OP_RWCOMP) {
#ifdef COORD_DEBUG
        std::cout << main_time << " issuing mmio " << op->mmio_op << std::endl;
#endif
        pci_rwcomp_issue(op->mmio_op);
      } else {
        throw "unknown type";
      }

      delete op;
    }
  }

 public:
  void dma_register(DMAOp *dma_op, bool ready) {
#ifdef COORD_DEBUG
    std::cout << main_time << " registering dma op " << dma_op << "  " << ready
              << std::endl;
#endif
    PCIOp *op = new PCIOp;
    op->dma_op = dma_op;
    op->type = PCIOp::OP_DMA;
    op->ready = ready;

    queue.push_back(op);
    dmamap[dma_op] = op;

    process();
  }

  void dma_mark_ready(DMAOp *op) {
#ifdef COORD_DEBUG
    std::cout << main_time << " readying dma op " << op << std::endl;
#endif
    dmamap[op]->ready = true;

    process();
  }

  void msi_enqueue(uint32_t vec) {
#ifdef COORD_DEBUG
    std::cout << main_time << " enqueuing MSI " << vec << std::endl;
#endif
    PCIOp *op = new PCIOp;
    op->msi_vec = vec;
    op->type = PCIOp::OP_MSI;
    op->ready = true;
    queue.push_back(op);

    process();
  }

  void mmio_comp_enqueue(MMIOOp *mmio_op) {
#ifdef COORD_DEBUG
    std::cout << main_time << " enqueuing MMIO comp " << mmio_op << std::endl;
#endif
    PCIOp *op = new PCIOp;
    op->mmio_op = mmio_op;
    op->type = PCIOp::OP_RWCOMP;
    op->ready = true;
    queue.push_back(op);

    process();
  }
};

#endif  // COORD_H_
