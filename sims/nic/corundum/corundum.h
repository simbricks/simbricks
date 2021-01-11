#ifndef CORUNDUM_H_
#define CORUNDUM_H_

#include "dma.h"

extern uint64_t main_time;

void pci_dma_issue(DMAOp *op);

#endif /* ndef CORUNDUM_H_ */
