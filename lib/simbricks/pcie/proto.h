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

#ifndef SIMBRICKS_PCIE_PROTO_H_
#define SIMBRICKS_PCIE_PROTO_H_

#include <assert.h>
#include <stdint.h>

#include <simbricks/base/proto.h>

/******************************************************************************/
/* Initialization messages on Unix socket */

/** Number of PCI bars */
#define SIMBRICKS_PROTO_PCIE_NBARS 6

/** in bars.flags: this is an I/O port bar. (otherwise memory) */
#define SIMBRICKS_PROTO_PCIE_BAR_IO (1 << 0)
/** in bars.flags: this is a 64-bit bar. (otherwise 32-bit only) */
#define SIMBRICKS_PROTO_PCIE_BAR_64 (1 << 1)
/** in bars.flags: this memory bar is prefetchable */
#define SIMBRICKS_PROTO_PCIE_BAR_PF (1 << 2)
/** in bars.flags: this memory bar is a dummy bar (device doesn't get MMIO
 * messages for this, but it dose get exposed to software. used for MSI-X). */
#define SIMBRICKS_PROTO_PCIE_BAR_DUMMY (1 << 3)

/**
 * welcome message sent by device to host. This message comes with the shared
 * memory file descriptor attached.
 */
struct SimbricksProtoPcieDevIntro {
  /** information for each BAR exposed by the device */
  struct {
    /** length of the bar in bytes (len = 0 indicates unused bar) */
    uint64_t len;
    /** flags (see SIMBRICKS_PROTO_PCIE_BAR_*) */
    uint64_t flags;
  } __attribute__((packed)) bars[SIMBRICKS_PROTO_PCIE_NBARS];

  /** PCI vendor id */
  uint16_t pci_vendor_id;
  /** PCI device id */
  uint16_t pci_device_id;
  /* PCI class */
  uint8_t pci_class;
  /* PCI subclass */
  uint8_t pci_subclass;
  /* PCI revision */
  uint8_t pci_revision;
  /* PCI prog if */
  uint8_t pci_progif;

  /* PCI number of MSI vectors */
  uint8_t pci_msi_nvecs;

  /* PCI number of MSI-X vectors */
  uint16_t pci_msix_nvecs;
  /* BAR number for MSI-X table */
  uint8_t pci_msix_table_bar;
  /* BAR number for MSI-X PBA */
  uint8_t pci_msix_pba_bar;
  /* Offset for MSI-X table */
  uint32_t pci_msix_table_offset;
  /* Offset for MSI-X PBA */
  uint32_t pci_msix_pba_offset;
  /* MSI-X capability offset */
  uint16_t psi_msix_cap_offset;
} __attribute__((packed));


/** welcome message sent by host to device */
struct SimbricksProtoPcieHostIntro {
} __attribute__((packed));

/******************************************************************************/
/* Messages on in-memory device to host channel */

/** Mask for type value in own_type field */
#define SIMBRICKS_PROTO_PCIE_D2H_MSG_READ 0x40
#define SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITE 0x41
#define SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT 0x42
#define SIMBRICKS_PROTO_PCIE_D2H_MSG_READCOMP 0x43
#define SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITECOMP 0x44

struct SimbricksProtoPcieD2HRead {
  uint64_t req_id;
  uint64_t offset;
  uint16_t len;
  uint8_t pad[30];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieD2HRead);

struct SimbricksProtoPcieD2HWrite {
  uint64_t req_id;
  uint64_t offset;
  uint16_t len;
  uint8_t pad[30];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
  uint8_t data[];
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieD2HWrite);

#define SIMBRICKS_PROTO_PCIE_INT_LEGACY_HI 0
#define SIMBRICKS_PROTO_PCIE_INT_LEGACY_LO 1
#define SIMBRICKS_PROTO_PCIE_INT_MSI 2
#define SIMBRICKS_PROTO_PCIE_INT_MSIX 3

struct SimbricksProtoPcieD2HInterrupt {
  uint16_t vector;
  uint8_t inttype;
  uint8_t pad[45];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieD2HInterrupt);

struct SimbricksProtoPcieD2HReadcomp {
  uint64_t req_id;
  uint8_t pad[40];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
  uint8_t data[];
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieD2HReadcomp);

struct SimbricksProtoPcieD2HWritecomp {
  uint64_t req_id;
  uint8_t pad[40];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieD2HWritecomp);

union SimbricksProtoPcieD2H {
  union SimbricksProtoBaseMsg base;
  struct SimbricksProtoPcieD2HRead read;
  struct SimbricksProtoPcieD2HWrite write;
  struct SimbricksProtoPcieD2HInterrupt interrupt;
  struct SimbricksProtoPcieD2HReadcomp readcomp;
  struct SimbricksProtoPcieD2HWritecomp writecomp;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(union SimbricksProtoPcieD2H);

/******************************************************************************/
/* Messages on in-memory host to device channel */

#define SIMBRICKS_PROTO_PCIE_H2D_MSG_READ 0x60
#define SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITE 0x61
#define SIMBRICKS_PROTO_PCIE_H2D_MSG_READCOMP 0x62
#define SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITECOMP 0x63
#define SIMBRICKS_PROTO_PCIE_H2D_MSG_DEVCTRL 0x64

struct SimbricksProtoPcieH2DRead {
  uint64_t req_id;
  uint64_t offset;
  uint16_t len;
  uint8_t bar;
  uint8_t pad[29];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieH2DRead);

struct SimbricksProtoPcieH2DWrite {
  uint64_t req_id;
  uint64_t offset;
  uint16_t len;
  uint8_t bar;
  uint8_t pad[29];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
  uint8_t data[];
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieH2DWrite);

struct SimbricksProtoPcieH2DReadcomp {
  uint64_t req_id;
  uint8_t pad[40];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
  uint8_t data[];
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieH2DReadcomp);

struct SimbricksProtoPcieH2DWritecomp {
  uint64_t req_id;
  uint8_t pad[40];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieH2DWritecomp);

#define SIMBRICKS_PROTO_PCIE_CTRL_INTX_EN (1 << 0)
#define SIMBRICKS_PROTO_PCIE_CTRL_MSI_EN (1 << 1)
#define SIMBRICKS_PROTO_PCIE_CTRL_MSIX_EN (1 << 2)
struct SimbricksProtoPcieH2DDevctrl {
  uint64_t flags;
  uint8_t pad[40];
  uint64_t timestamp;
  uint8_t pad_[7];
  uint8_t own_type;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(struct SimbricksProtoPcieH2DDevctrl);

union SimbricksProtoPcieH2D {
  union SimbricksProtoBaseMsg base;
  struct SimbricksProtoPcieH2DRead read;
  struct SimbricksProtoPcieH2DWrite write;
  struct SimbricksProtoPcieH2DReadcomp readcomp;
  struct SimbricksProtoPcieH2DWritecomp writecomp;
  struct SimbricksProtoPcieH2DDevctrl devctrl;
} __attribute__((packed));
SIMBRICKS_PROTO_MSG_SZCHECK(union SimbricksProtoPcieH2D);

#endif  // SIMBRICKS_PCIE_PROTO_H_
