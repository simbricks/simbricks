#ifndef COORD_H_
#define COORD_H_

#include <deque>
#include <map>
#include <iostream>

#include "debug.h"

class DMAOp;

void pci_dma_issue(DMAOp *op);
void pci_msi_issue(uint8_t vec);

class PCICoordinator {
    protected:
        struct PCIOp {
            union {
                DMAOp *dma_op;
                uint32_t msi_vec;
            };
            bool isDma;
            bool ready;
        };

        std::deque<PCIOp *> queue;
        std::map<DMAOp *, PCIOp *> dmamap;

        void process()
        {
            PCIOp *op;
            while (!queue.empty()) {
                op = queue.front();
                if (!op->ready)
                    break;

                queue.pop_front();
                if (!op->isDma) {
#ifdef COORD_DEBUG
                    std::cout << "issuing msi " << op->msi_vec << std::endl;
#endif
                    pci_msi_issue(op->msi_vec);
                } else {
#ifdef COORD_DEBUG
                    std::cout << "issuing dma " << op->dma_op << std::endl;
#endif
                    pci_dma_issue(op->dma_op);
                    dmamap.erase(op->dma_op);
                }
                delete op;
            }
        }

    public:
        void dma_register(DMAOp *dma_op, bool ready)
        {
#ifdef COORD_DEBUG
            std::cout << "registering dma op " << dma_op << "  " << ready << std::endl;
#endif
            PCIOp *op = new PCIOp;
            op->dma_op = dma_op;
            op->isDma = true;
            op->ready = ready;

            queue.push_back(op);
            dmamap[dma_op] = op;

            process();
        }

        void dma_mark_ready(DMAOp *op)
        {
#ifdef COORD_DEBUG
            std::cout << "readying dma op " << op <<  std::endl;
#endif
            dmamap[op]->ready = true;

            process();
        }

        void msi_enqueue(uint32_t vec)
        {
#ifdef COORD_DEBUG
            std::cout << "enqueuing MSI " << vec <<  std::endl;
#endif
            PCIOp *op = new PCIOp;
            op->msi_vec = vec;
            op->isDma = false;
            op->ready = true;
            queue.push_back(op);

            process();
        }
};



#endif
