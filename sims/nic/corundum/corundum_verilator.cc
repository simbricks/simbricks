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

#include <signal.h>
#include <verilated.h>

#include <deque>
#include <iostream>
#include <set>
#ifdef TRACE_ENABLED
#include <verilated_vcd_c.h>
#endif

extern "C" {
#include <simbricks/nicif/nicsim.h>
}

#include "sims/nic/corundum/coord.h"
#include "sims/nic/corundum/corundum.h"
#include "sims/nic/corundum/debug.h"
#include "sims/nic/corundum/dma.h"
#include "sims/nic/corundum/mem.h"
#include "sims/nic/corundum/obj_dir/Vinterface.h"

struct DMAOp;

static uint64_t clock_period = 4 * 1000ULL;   // 4ns -> 250MHz
static uint64_t sync_period = 500 * 1000ULL;  // 500ns
static uint64_t pci_latency = 500 * 1000ULL;  // 500ns
static uint64_t eth_latency = 500 * 1000ULL;  // 500ns

static volatile int exiting = 0;
uint64_t main_time = 0;
static struct nicsim_params nsparams;
#ifdef TRACE_ENABLED
static VerilatedVcdC *trace;
#endif

static volatile union cosim_pcie_proto_d2h *d2h_alloc(void);

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  fprintf(stderr, "main_time = %lu\n", main_time);
}

double sc_time_stamp() {
  return main_time;
}

static void reset_inputs(Vinterface *top) {
  top->clk = 0;
  top->rst = 0;
  top->m_axis_ctrl_dma_read_desc_ready = 0;
  top->s_axis_ctrl_dma_read_desc_status_tag = 0;
  top->s_axis_ctrl_dma_read_desc_status_valid = 0;
  top->m_axis_ctrl_dma_write_desc_ready = 0;
  top->s_axis_ctrl_dma_write_desc_status_tag = 0;
  top->s_axis_ctrl_dma_write_desc_status_valid = 0;
  top->m_axis_data_dma_read_desc_ready = 0;
  top->s_axis_data_dma_read_desc_status_tag = 0;
  top->s_axis_data_dma_read_desc_status_valid = 0;
  top->m_axis_data_dma_write_desc_ready = 0;
  top->s_axis_data_dma_write_desc_status_tag = 0;
  top->s_axis_data_dma_write_desc_status_valid = 0;
  top->s_axil_awaddr = 0;
  top->s_axil_awprot = 0;
  top->s_axil_awvalid = 0;
  top->s_axil_wdata = 0;
  top->s_axil_wstrb = 0;
  top->s_axil_wvalid = 0;
  top->s_axil_bready = 0;
  top->s_axil_araddr = 0;
  top->s_axil_arprot = 0;
  top->s_axil_arvalid = 0;
  top->s_axil_rready = 0;
  top->m_axil_csr_awready = 0;
  top->m_axil_csr_wready = 0;
  top->m_axil_csr_bresp = 0;
  top->m_axil_csr_bvalid = 0;
  top->m_axil_csr_arready = 0;
  top->m_axil_csr_rdata = 0;
  top->m_axil_csr_rresp = 0;
  top->m_axil_csr_rvalid = 0;
  top->ctrl_dma_ram_wr_cmd_sel = 0;
  // top->ctrl_dma_ram_wr_cmd_be = 0;
  // top->ctrl_dma_ram_wr_cmd_addr = 0;
  top->ctrl_dma_ram_wr_cmd_valid = 0;
  top->ctrl_dma_ram_rd_cmd_sel = 0;
  // top->ctrl_dma_ram_rd_cmd_addr = 0;
  top->ctrl_dma_ram_rd_cmd_valid = 0;
  top->ctrl_dma_ram_rd_resp_ready = 0;
  top->data_dma_ram_wr_cmd_sel = 0;
  // top->data_dma_ram_wr_cmd_be = 0;
  // top->data_dma_ram_wr_cmd_addr = 0;
  top->data_dma_ram_wr_cmd_valid = 0;
  top->data_dma_ram_rd_cmd_sel = 0;
  // top->data_dma_ram_rd_cmd_addr = 0;
  top->data_dma_ram_rd_cmd_valid = 0;
  top->data_dma_ram_rd_resp_ready = 0;
  top->tx_axis_tready = 0;
  top->s_axis_tx_ptp_ts_valid = 0;
  top->rx_axis_tkeep = 0;
  top->rx_axis_tvalid = 0;
  top->rx_axis_tlast = 0;
  top->rx_axis_tuser = 0;
  top->s_axis_rx_ptp_ts_valid = 0;
  top->ptp_ts_step = 0;
}

static void report_output(const char *label, uint64_t val) {
  if (val == 0)
    return;

  std::cout << "    " << label << " = " << val << std::endl;
}

static void report_outputs(Vinterface *top) {
  report_output("m_axis_ctrl_dma_read_desc_dma_addr",
                top->m_axis_ctrl_dma_read_desc_dma_addr);
  report_output("m_axis_ctrl_dma_read_desc_ram_sel",
                top->m_axis_ctrl_dma_read_desc_ram_sel);
  report_output("m_axis_ctrl_dma_read_desc_ram_addr",
                top->m_axis_ctrl_dma_read_desc_ram_addr);
  report_output("m_axis_ctrl_dma_read_desc_len",
                top->m_axis_ctrl_dma_read_desc_len);
  report_output("m_axis_ctrl_dma_read_desc_tag",
                top->m_axis_ctrl_dma_read_desc_tag);
  report_output("m_axis_ctrl_dma_read_desc_valid",
                top->m_axis_ctrl_dma_read_desc_valid);
  report_output("m_axis_ctrl_dma_write_desc_dma_addr",
                top->m_axis_ctrl_dma_write_desc_dma_addr);
  report_output("m_axis_ctrl_dma_write_desc_ram_sel",
                top->m_axis_ctrl_dma_write_desc_ram_sel);
  report_output("m_axis_ctrl_dma_write_desc_ram_addr",
                top->m_axis_ctrl_dma_write_desc_ram_addr);
  report_output("m_axis_ctrl_dma_write_desc_len",
                top->m_axis_ctrl_dma_write_desc_len);
  report_output("m_axis_ctrl_dma_write_desc_tag",
                top->m_axis_ctrl_dma_write_desc_tag);
  report_output("m_axis_ctrl_dma_write_desc_valid",
                top->m_axis_ctrl_dma_write_desc_valid);
  report_output("m_axis_data_dma_read_desc_dma_addr",
                top->m_axis_data_dma_read_desc_dma_addr);
  report_output("m_axis_data_dma_read_desc_ram_sel",
                top->m_axis_data_dma_read_desc_ram_sel);
  report_output("m_axis_data_dma_read_desc_ram_addr",
                top->m_axis_data_dma_read_desc_ram_addr);
  report_output("m_axis_data_dma_read_desc_len",
                top->m_axis_data_dma_read_desc_len);
  report_output("m_axis_data_dma_read_desc_tag",
                top->m_axis_data_dma_read_desc_tag);
  report_output("m_axis_data_dma_read_desc_valid",
                top->m_axis_data_dma_read_desc_valid);
  report_output("m_axis_data_dma_write_desc_dma_addr",
                top->m_axis_data_dma_write_desc_dma_addr);
  report_output("m_axis_data_dma_write_desc_ram_sel",
                top->m_axis_data_dma_write_desc_ram_sel);
  report_output("m_axis_data_dma_write_desc_ram_addr",
                top->m_axis_data_dma_write_desc_ram_addr);
  report_output("m_axis_data_dma_write_desc_len",
                top->m_axis_data_dma_write_desc_len);
  report_output("m_axis_data_dma_write_desc_tag",
                top->m_axis_data_dma_write_desc_tag);
  report_output("m_axis_data_dma_write_desc_valid",
                top->m_axis_data_dma_write_desc_valid);
  report_output("s_axil_awready", top->s_axil_awready);
  report_output("s_axil_wready", top->s_axil_wready);
  report_output("s_axil_bresp", top->s_axil_bresp);
  report_output("s_axil_bvalid", top->s_axil_bvalid);
  report_output("s_axil_arready", top->s_axil_arready);
  report_output("s_axil_rdata", top->s_axil_rdata);
  report_output("s_axil_rresp", top->s_axil_rresp);
  report_output("s_axil_rvalid", top->s_axil_rvalid);
  report_output("m_axil_csr_awaddr", top->m_axil_csr_awaddr);
  report_output("m_axil_csr_awprot", top->m_axil_csr_awprot);
  report_output("m_axil_csr_awvalid", top->m_axil_csr_awvalid);
  report_output("m_axil_csr_wdata", top->m_axil_csr_wdata);
  report_output("m_axil_csr_wstrb", top->m_axil_csr_wstrb);
  report_output("m_axil_csr_wvalid", top->m_axil_csr_wvalid);
  report_output("m_axil_csr_bready", top->m_axil_csr_bready);
  report_output("m_axil_csr_araddr", top->m_axil_csr_araddr);
  report_output("m_axil_csr_arprot", top->m_axil_csr_arprot);
  report_output("m_axil_csr_arvalid", top->m_axil_csr_arvalid);
  report_output("m_axil_csr_rready", top->m_axil_csr_rready);
  report_output("ctrl_dma_ram_wr_cmd_ready", top->ctrl_dma_ram_wr_cmd_ready);
  report_output("ctrl_dma_ram_rd_cmd_ready", top->ctrl_dma_ram_rd_cmd_ready);
  report_output("ctrl_dma_ram_rd_resp_valid", top->ctrl_dma_ram_rd_resp_valid);
  report_output("data_dma_ram_wr_cmd_ready", top->data_dma_ram_wr_cmd_ready);
  report_output("data_dma_ram_rd_cmd_ready", top->data_dma_ram_rd_cmd_ready);
  report_output("data_dma_ram_rd_resp_valid", top->data_dma_ram_rd_resp_valid);
  report_output("tx_axis_tkeep", top->tx_axis_tkeep);
  report_output("tx_axis_tvalid", top->tx_axis_tvalid);
  report_output("tx_axis_tlast", top->tx_axis_tlast);
  report_output("tx_axis_tuser", top->tx_axis_tuser);
  report_output("s_axis_tx_ptp_ts_ready", top->s_axis_tx_ptp_ts_ready);
  report_output("rx_axis_tready", top->rx_axis_tready);
  report_output("s_axis_rx_ptp_ts_ready", top->s_axis_rx_ptp_ts_ready);
  report_output("msi_irq", top->msi_irq);
}

struct MMIOOp {
  uint64_t id;
  uint64_t addr;
  uint64_t value;
  size_t len;
  bool isWrite;
};

class MMIOInterface {
 protected:
  enum OpState {
    AddrIssued,
    AddrAcked,
    AddrDone,
  };

  Vinterface &top;
  PCICoordinator &coord;
  std::deque<MMIOOp *> queue;
  MMIOOp *rCur, *wCur;
  enum OpState rState, wState;

 public:
  MMIOInterface(Vinterface &top_, PCICoordinator &coord_)
      : top(top_), coord(coord_), rCur(0), wCur(0) {
  }

  void step() {
    if (rCur) {
      /* work on active read operation */

      if (rState == AddrIssued && top.s_axil_arready) {
        /* read handshake is complete */
        top.s_axil_arvalid = 0;
        rState = AddrAcked;
      }
      if (rState == AddrAcked && top.s_axil_rvalid) {
        /* read data received */
        top.s_axil_rready = 0;
        rCur->value = top.s_axil_rdata;
        coord.mmio_comp_enqueue(rCur);
#ifdef MMIO_DEBUG
        std::cout << main_time << " MMIO: completed AXI read op=" << rCur
                  << " val=" << rCur->value << std::endl;
#endif
        rCur = 0;
      }
    } else if (wCur) {
      /* work on active write operation */

      if (wState == AddrIssued && top.s_axil_awready) {
        /* write addr handshake is complete */
        top.s_axil_awvalid = 0;
        wState = AddrAcked;
      }
      if (wState == AddrAcked && top.s_axil_wready) {
        /* write data handshake is complete */
        top.s_axil_wvalid = 0;
        top.s_axil_bready = 1;
        wState = AddrDone;
      }
      if (wState == AddrDone && top.s_axil_bvalid) {
        /* write complete */
        top.s_axil_bready = 0;
        // TODO(antoinek): check top.s_axil_bresp
#ifdef MMIO_DEBUG
        std::cout << main_time << " MMIO: completed AXI write op=" << wCur
                  << std::endl;
#endif
        coord.mmio_comp_enqueue(wCur);
        wCur = 0;
      }
    } else if (/*!top.clk &&*/ !queue.empty()) {
      /* issue new operation */

      MMIOOp *op = queue.front();
      queue.pop_front();
      if (!op->isWrite) {
        /* issue new read */
        rCur = op;

        rState = AddrIssued;

        top.s_axil_araddr = rCur->addr;
        top.s_axil_arprot = 0x0;
        top.s_axil_arvalid = 1;
        top.s_axil_rready = 1;
      } else {
        /* issue new write */
        wCur = op;

        wState = AddrIssued;

        top.s_axil_awaddr = wCur->addr;
        top.s_axil_awprot = 0x0;
        top.s_axil_awvalid = 1;

        top.s_axil_wdata = wCur->value;
        top.s_axil_wstrb = 0xf;
        top.s_axil_wvalid = 1;
      }
    }
  }

  void issueRead(uint64_t id, uint64_t addr, size_t len) {
    MMIOOp *op = new MMIOOp;
#ifdef MMIO_DEBUG
    std::cout << main_time << " MMIO: read id=" << id << " addr=" << std::hex
              << addr << " len=" << len << " op=" << op << std::endl;
#endif
    op->id = id;
    op->addr = addr;
    op->len = len;
    op->isWrite = false;
    queue.push_back(op);
  }

  void issueWrite(uint64_t id, uint64_t addr, size_t len, uint64_t val) {
    MMIOOp *op = new MMIOOp;
#ifdef MMIO_DEBUG
    std::cout << main_time << " MMIO: write id=" << id << " addr=" << std::hex
              << addr << " len=" << len << " val=" << val << " op=" << op
              << std::endl;
#endif
    op->id = id;
    op->addr = addr;
    op->len = len;
    op->value = val;
    op->isWrite = true;
    queue.push_back(op);
  }
};

void pci_rwcomp_issue(MMIOOp *op) {
  volatile union cosim_pcie_proto_d2h *msg = d2h_alloc();
  volatile struct cosim_pcie_proto_d2h_readcomp *rc;
  volatile struct cosim_pcie_proto_d2h_writecomp *wc;

  if (!msg)
    throw "completion alloc failed";

  if (op->isWrite) {
    wc = &msg->writecomp;
    wc->req_id = op->id;

    // WMB();
    wc->own_type =
        COSIM_PCIE_PROTO_D2H_MSG_WRITECOMP | COSIM_PCIE_PROTO_D2H_OWN_HOST;
  } else {
    rc = &msg->readcomp;
    memcpy((void *)rc->data, &op->value, op->len);
    rc->req_id = op->id;

    // WMB();
    rc->own_type =
        COSIM_PCIE_PROTO_D2H_MSG_READCOMP | COSIM_PCIE_PROTO_D2H_OWN_HOST;
  }

  delete op;
}

#if 0
class MemAccessor {
    protected:
        Vinterface &top;

        /* outputs to memory */
        vluint8_t   &p_mem_sel;
        vluint32_t (*p_mem_be)[4]; /* for write only */
        vluint32_t (&p_mem_addr)[3];
        vluint8_t   &p_mem_valid;
        vluint8_t   *p_mem_resp_ready; /* for read only */

        /* direction depends */
        vluint32_t (&p_mem_data)[32];

        /* inputs from memory */
        vluint8_t   &p_mem_ready;
        vluint8_t   *p_mem_resp_valid; /* for read only */

    public:
        MemAccessor(Vinterface &top_, bool read,
                vluint8_t &p_mem_sel_,
                vluint32_t (*p_mem_be_)[4],
                vluint32_t (&p_mem_addr_)[3],
                vluint8_t &p_mem_valid_,
                vluint8_t *p_mem_resp_ready_,
                vluint32_t (&p_mem_data_)[32],
                vluint8_t &p_mem_ready_,
                vluint8_t *p_mem_resp_valid_)
            : top(top_),
            p_mem_sel(p_mem_sel_), p_mem_be(p_mem_be_), p_mem_addr(p_mem_addr_),
            p_mem_valid(p_mem_valid_), p_mem_resp_ready(p_mem_resp_ready_),
            p_mem_data(p_mem_data_), p_mem_ready(p_mem_ready_),
            p_mem_resp_valid(p_mem_resp_valid_)
        {
        }

        void step()
        {
        }
};
#endif

std::set<DMAOp *> pci_dma_pending;

void pci_dma_issue(DMAOp *op) {
  volatile union cosim_pcie_proto_d2h *msg = d2h_alloc();
  uint8_t ty;

  if (!msg)
    throw "completion alloc failed";

  if (op->write) {
    volatile struct cosim_pcie_proto_d2h_write *write = &msg->write;
    write->req_id = (uintptr_t)op;
    write->offset = op->dma_addr;
    write->len = op->len;

    // TODO(antoinek): check DMA length
    memcpy((void *)write->data, op->data, op->len);

    // WMB();
    write->own_type =
        COSIM_PCIE_PROTO_D2H_MSG_WRITE | COSIM_PCIE_PROTO_D2H_OWN_HOST;
  } else {
    volatile struct cosim_pcie_proto_d2h_read *read = &msg->read;
    read->req_id = (uintptr_t)op;
    read->offset = op->dma_addr;
    read->len = op->len;

    // WMB();
    read->own_type =
        COSIM_PCIE_PROTO_D2H_MSG_READ | COSIM_PCIE_PROTO_D2H_OWN_HOST;
  }

  pci_dma_pending.insert(op);
}

static void h2d_readcomp(volatile struct cosim_pcie_proto_h2d_readcomp *rc) {
  DMAOp *op = (DMAOp *)(uintptr_t)rc->req_id;
  if (pci_dma_pending.find(op) == pci_dma_pending.end())
    throw "unexpected completion";
  pci_dma_pending.erase(op);

  memcpy(op->data, (void *)rc->data, op->len);

#if 0
    std::cerr << "dma read comp: ";
    for (size_t i = 0; i < op->len; i++)
        std::cerr << (unsigned) op->data[i] << " ";
    std::cerr << std::endl;
#endif

  op->engine->pci_op_complete(op);
}

static void h2d_writecomp(volatile struct cosim_pcie_proto_h2d_writecomp *wc) {
  DMAOp *op = (DMAOp *)(uintptr_t)wc->req_id;
  if (pci_dma_pending.find(op) == pci_dma_pending.end())
    throw "unexpected completion";
  pci_dma_pending.erase(op);

  op->engine->pci_op_complete(op);
}

static uint64_t csr_read(uint64_t off) {
  switch (off) {
    case 0x00:
      return 32; /* firmware id */
    case 0x04:
      return 1; /* firmware version */
    case 0x08:
      return 0x43215678; /* board id */
    case 0x0c:
      return 0x1; /* board version */
    case 0x10:
      return 1; /* phc count */
    case 0x14:
      return 0x200; /* phc offset */
    case 0x18:
      return 0x80; /* phc stride */
    case 0x20:
      return 1; /* if_count */
    case 0x24:
      return 0x80000; /* if stride */
    case 0x2c:
      return 0x80000; /* if csr offset */
    case 0x200:
      return 0x1; /* phc features */
    default:
      std::cerr << "csr_read(" << off << ") unimplemented" << std::endl;
      return 0;
  }
}

static void csr_write(uint64_t off, uint64_t val) {
}

static void h2d_read(MMIOInterface &mmio,
                     volatile struct cosim_pcie_proto_h2d_read *read) {
  // std::cout << "got read " << read->offset << std::endl;
  if (read->offset < 0x80000) {
    volatile union cosim_pcie_proto_d2h *msg = d2h_alloc();
    volatile struct cosim_pcie_proto_d2h_readcomp *rc;

    if (!msg)
      throw "completion alloc failed";

    rc = &msg->readcomp;
    memset((void *)rc->data, 0, read->len);
    uint64_t val = csr_read(read->offset);
    memcpy((void *)rc->data, &val, read->len);
    rc->req_id = read->req_id;

    // WMB();
    rc->own_type =
        COSIM_PCIE_PROTO_D2H_MSG_READCOMP | COSIM_PCIE_PROTO_D2H_OWN_HOST;
  } else {
    /*printf("read(bar=%u, off=%lu, len=%u) = %lu\n", read->bar, read->offset,
            read->len, val);*/
    mmio.issueRead(read->req_id, read->offset, read->len);
  }
}

static void h2d_write(MMIOInterface &mmio,
                      volatile struct cosim_pcie_proto_h2d_write *write) {
  uint64_t val = 0;

  memcpy(&val, (void *)write->data, write->len);

  // std::cout << "got write " << write->offset << " = " << val << std::endl;

  if (write->offset < 0x80000) {
    volatile union cosim_pcie_proto_d2h *msg = d2h_alloc();
    volatile struct cosim_pcie_proto_d2h_writecomp *wc;

    if (!msg)
      throw "completion alloc failed";

    csr_write(write->offset, val);

    wc = &msg->writecomp;
    wc->req_id = write->req_id;

    // WMB();
    wc->own_type =
        COSIM_PCIE_PROTO_D2H_MSG_WRITECOMP | COSIM_PCIE_PROTO_D2H_OWN_HOST;
  } else {
    mmio.issueWrite(write->req_id, write->offset, write->len, val);
  }
}

static void poll_h2d(MMIOInterface &mmio) {
  volatile union cosim_pcie_proto_h2d *msg =
      nicif_h2d_poll(&nsparams, main_time);
  uint8_t t;

  if (msg == NULL)
    return;

  t = msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_MSG_MASK;

  // std::cerr << "poll_h2d: polled type=" << (int) t << std::endl;
  switch (t) {
    case COSIM_PCIE_PROTO_H2D_MSG_READ:
      h2d_read(mmio, &msg->read);
      break;

    case COSIM_PCIE_PROTO_H2D_MSG_WRITE:
      h2d_write(mmio, &msg->write);
      break;

    case COSIM_PCIE_PROTO_H2D_MSG_READCOMP:
      h2d_readcomp(&msg->readcomp);
      break;

    case COSIM_PCIE_PROTO_H2D_MSG_WRITECOMP:
      h2d_writecomp(&msg->writecomp);
      break;

    case COSIM_PCIE_PROTO_H2D_MSG_DEVCTRL:
      break;

    case COSIM_PCIE_PROTO_H2D_MSG_SYNC:
      break;

    default:
      std::cerr << "poll_h2d: unsupported type=" << t << std::endl;
  }

  nicif_h2d_done(msg);
  nicif_h2d_next();
}

static volatile union cosim_pcie_proto_d2h *d2h_alloc(void) {
  return nicsim_d2h_alloc(&nsparams, main_time);
}

class EthernetTx {
 protected:
  Vinterface &top;
  uint8_t packet_buf[2048];
  size_t packet_len;

 public:
  EthernetTx(Vinterface &top_) : top(top_), packet_len(0) {
  }

  void packet_done() {
    volatile union cosim_eth_proto_d2n *msg =
        nicsim_d2n_alloc(&nsparams, main_time);
    volatile struct cosim_eth_proto_d2n_send *send;

    if (!msg)
      throw "completion alloc failed";

    send = &msg->send;
    memcpy((void *)send->data, packet_buf, packet_len);
    send->len = packet_len;
    send->timestamp = main_time + eth_latency;

    // WMB();
    send->own_type = COSIM_ETH_PROTO_D2N_MSG_SEND | COSIM_ETH_PROTO_D2N_OWN_NET;

#ifdef ETH_DEBUG
    std::cerr << main_time << " EthernetTx: packet len=" << std::hex
              << packet_len << " ";
    for (size_t i = 0; i < packet_len; i++) {
      std::cerr << (unsigned)packet_buf[i] << " ";
    }
    std::cerr << std::endl;
#endif
  }

  void step() {
    top.tx_axis_tready = 1;

    if (top.tx_axis_tvalid) {
      /* iterate over all 8 bytes */
      for (size_t i = 0; i < 8; i++) {
        if ((top.tx_axis_tkeep & (1 << i)) != 0) {
          assert(packet_len < 2048);
          packet_buf[packet_len++] = (top.tx_axis_tdata >> (i * 8));
        }
      }

      if (top.tx_axis_tlast) {
        packet_done();
        packet_len = 0;
      }
    }
  }
};

class EthernetRx {
 protected:
  Vinterface &top;

  static const size_t FIFO_SIZE = 32;
  uint8_t fifo_bufs[FIFO_SIZE][2048];
  size_t fifo_lens[FIFO_SIZE];
  size_t fifo_pos_rd;
  size_t fifo_pos_wr;

  size_t packet_off;

 public:
  EthernetRx(Vinterface &top_)
      : top(top_), fifo_pos_rd(0), fifo_pos_wr(0), packet_off(0) {
    for (size_t i = 0; i < FIFO_SIZE; i++) fifo_lens[i] = 0;
  }

  void packet_received(const void *data, size_t len) {
    if (fifo_lens[fifo_pos_wr] != 0) {
      std::cerr << "EthernetRx: dropping packet" << std::endl;
      return;
    }

    memcpy(fifo_bufs[fifo_pos_wr], data, len);
    fifo_lens[fifo_pos_wr] = len;

#ifdef ETH_DEBUG
    std::cout << main_time << " rx into " << fifo_pos_wr << std::endl;
    std::cerr << main_time << " EthernetRx: packet len=" << std::hex << len
              << " ";
    for (size_t i = 0; i < len; i++) {
      std::cerr << (unsigned)fifo_bufs[fifo_pos_wr][i] << " ";
    }
    std::cerr << std::endl;
#endif

    fifo_pos_wr = (fifo_pos_wr + 1) % FIFO_SIZE;
  }

  void step() {
    if (fifo_lens[fifo_pos_rd] != 0) {
      // we have data to send
      if (packet_off != 0 && !top.rx_axis_tready) {
        // no ready signal, can't advance
        std::cerr << "eth rx: no ready" << std::endl;
      } else if (packet_off == fifo_lens[fifo_pos_rd]) {
        // done with packet
#ifdef ETH_DEBUG
        std::cerr << main_time << " EthernetRx: finished packet" << std::endl;
#endif
        top.rx_axis_tvalid = 0;
        top.rx_axis_tlast = 0;

        packet_off = 0;
        fifo_lens[fifo_pos_rd] = 0;
        fifo_pos_rd = (fifo_pos_rd + 1) % FIFO_SIZE;
      } else {
        // put out more packet data
#ifdef ETH_DEBUG
        std::cerr << main_time << " EthernetRx: push flit " << packet_off
                  << std::endl;
        if (packet_off == 0)
          std::cout << "rx from " << fifo_pos_rd << std::endl;
#endif
        top.rx_axis_tkeep = 0;
        top.rx_axis_tdata = 0;
        size_t i;
        for (i = 0; i < 8 && packet_off < fifo_lens[fifo_pos_rd]; i++) {
          top.rx_axis_tdata |= ((uint64_t)fifo_bufs[fifo_pos_rd][packet_off])
                               << (i * 8);
          top.rx_axis_tkeep |= (1 << i);
          packet_off++;
        }
        top.rx_axis_tvalid = 1;
        top.rx_axis_tlast = (packet_off == fifo_lens[fifo_pos_rd]);
      }
      //  trace->dump(main_time);
    } else {
      // no data
      top.rx_axis_tvalid = 0;
      top.rx_axis_tlast = 0;
    }
  }
};

static void n2d_recv(EthernetRx &rx,
                     volatile struct cosim_eth_proto_n2d_recv *recv) {
  rx.packet_received((const void *)recv->data, recv->len);
}

static void poll_n2d(EthernetRx &rx) {
  volatile union cosim_eth_proto_n2d *msg =
      nicif_n2d_poll(&nsparams, main_time);
  uint8_t t;

  if (msg == NULL)
    return;

  t = msg->dummy.own_type & COSIM_ETH_PROTO_N2D_MSG_MASK;

  switch (t) {
    case COSIM_ETH_PROTO_N2D_MSG_RECV:
      n2d_recv(rx, &msg->recv);
      break;

    case COSIM_ETH_PROTO_N2D_MSG_SYNC:
      break;

    default:
      std::cerr << "poll_n2d: unsupported type=" << t << std::endl;
  }

  nicif_n2d_done(msg);
  nicif_n2d_next();
}

#if 0
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

        Vinterface &top;
        std::deque<PCIOp *> queue;
        std::map<DMAOp *, PCIOp *> dmamap;

        void process()
        {
            PCIOp *op;
            while (queue.empty()) {
                op = queue.front();
                if (!op->ready)
                    break;

                queue.pop_front();
                if (!op->isDma) {
                    pci_msi_issue(op->msi_vec);
                    delete op;
                } else {
                    pci_dma_issue(op->dma_op);
                    dmamap.erase(op->dma_op);
                    delete op;
                }
            }
        }

    public:
        PCICoordinator(Vinterface &top_)
            : top(top_)
        {
        }

        void dma_register(DMAOp *dma_op, bool ready)
        {
            PCIOp *op = new PCIOp;
            op->dma_op = vec;
            op->isDma = true;
            op->ready = ready;

            queue.push_back(op);
            dmamap[op] = dma_op;

            process();
        }

        void dma_mark_ready(DMAOp *op)
        {
            dmamap[op]->ready = true;

            process();
        }

        void msi_enqueue(uint32_t vec)
        {
            PCIOp *op = new PCIOp;
            op->msi_vec = vec;
            op->isDma = false;
            op->ready = true;
            queue.push_back(op);

            process();
        }
};
#endif

void pci_msi_issue(uint8_t vec) {
  volatile union cosim_pcie_proto_d2h *msg = d2h_alloc();
  volatile struct cosim_pcie_proto_d2h_interrupt *intr;

#ifdef MSI_DEBUG
  std::cerr << main_time << " MSI interrupt vec=" << (int)vec << std::endl;
#endif

  intr = &msg->interrupt;
  intr->vector = vec;
  intr->inttype = COSIM_PCIE_PROTO_INT_MSI;

  // WMB();
  intr->own_type =
      COSIM_PCIE_PROTO_D2H_MSG_INTERRUPT | COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

static void msi_step(Vinterface &top, PCICoordinator &coord) {
  if (!top.msi_irq)
    return;

#ifdef MSI_DEBUG
  std::cerr << main_time
            << " msi_step: MSI interrupt raw vec=" << (int)top.msi_irq
            << std::endl;
#endif
  for (size_t i = 0; i < 32; i++) {
    if (!((1ULL << i) & top.msi_irq))
      continue;
    coord.msi_enqueue(i);
  }
}

int main(int argc, char *argv[]) {
  char *vargs[2] = {argv[0], NULL};
  Verilated::commandArgs(1, vargs);
  int sync_mode = SYNC_MODES;
#ifdef TRACE_ENABLED
  Verilated::traceEverOn(true);
#endif

  if (argc < 4 && argc > 10) {
    fprintf(stderr,
            "Usage: corundum_verilator PCI-SOCKET ETH-SOCKET "
            "SHM [SYNC-MODE] [START-TICK] [SYNC-PERIOD] [PCI-LATENCY] "
            "[ETH-LATENCY] [CLOCK-FREQ-MHZ]\n");
    return EXIT_FAILURE;
  }
  if (argc >= 5)
    sync_mode = strtol(argv[4], NULL, 0);
  if (argc >= 6)
    main_time = strtoull(argv[5], NULL, 0);
  if (argc >= 7)
    sync_period = strtoull(argv[6], NULL, 0) * 1000ULL;
  if (argc >= 8)
    pci_latency = strtoull(argv[7], NULL, 0) * 1000ULL;
  if (argc >= 9)
    eth_latency = strtoull(argv[8], NULL, 0) * 1000ULL;
  if (argc >= 10)
    clock_period = 1000000ULL / strtoull(argv[9], NULL, 0);

  struct cosim_pcie_proto_dev_intro di;
  memset(&di, 0, sizeof(di));

  di.bars[0].len = 1 << 24;
  di.bars[0].flags = COSIM_PCIE_PROTO_BAR_64;

  di.pci_vendor_id = 0x5543;
  di.pci_device_id = 0x1001;
  di.pci_class = 0x02;
  di.pci_subclass = 0x00;
  di.pci_revision = 0x00;
  di.pci_msi_nvecs = 32;

  nsparams.sync_pci = 1;
  nsparams.sync_eth = 1;
  nsparams.pci_socket_path = argv[1];
  nsparams.eth_socket_path = argv[2];
  nsparams.shm_path = argv[3];
  nsparams.pci_latency = pci_latency;
  nsparams.eth_latency = eth_latency;
  nsparams.sync_delay = sync_period;
  assert(sync_mode == SYNC_MODES || sync_mode == SYNC_BARRIER);
  nsparams.sync_mode = sync_mode;

  if (nicsim_init(&nsparams, &di)) {
    return EXIT_FAILURE;
  }
  std::cout << "sync_pci=" << nsparams.sync_pci
            << "  sync_eth=" << nsparams.sync_eth << std::endl;

  signal(SIGINT, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  Vinterface *top = new Vinterface;
#ifdef TRACE_ENABLED
  trace = new VerilatedVcdC;
  top->trace(trace, 99);
  trace->open("debug.vcd");
#endif

  MemWritePort p_mem_write_ctrl_dma(
      top->ctrl_dma_ram_wr_cmd_sel, top->ctrl_dma_ram_wr_cmd_be,
      top->ctrl_dma_ram_wr_cmd_addr, top->ctrl_dma_ram_wr_cmd_data,
      top->ctrl_dma_ram_wr_cmd_valid, top->ctrl_dma_ram_wr_cmd_ready);
  MemReadPort p_mem_read_ctrl_dma(
      top->ctrl_dma_ram_rd_cmd_sel, top->ctrl_dma_ram_rd_cmd_addr,
      top->ctrl_dma_ram_rd_cmd_valid, top->ctrl_dma_ram_rd_resp_ready,
      top->ctrl_dma_ram_rd_resp_data, top->ctrl_dma_ram_rd_cmd_ready,
      top->ctrl_dma_ram_rd_resp_valid);
  MemWritePort p_mem_write_data_dma(
      top->data_dma_ram_wr_cmd_sel, top->data_dma_ram_wr_cmd_be,
      top->data_dma_ram_wr_cmd_addr, top->data_dma_ram_wr_cmd_data,
      top->data_dma_ram_wr_cmd_valid, top->data_dma_ram_wr_cmd_ready);
  MemReadPort p_mem_read_data_dma(
      top->data_dma_ram_rd_cmd_sel, top->data_dma_ram_rd_cmd_addr,
      top->data_dma_ram_rd_cmd_valid, top->data_dma_ram_rd_resp_ready,
      top->data_dma_ram_rd_resp_data, top->data_dma_ram_rd_cmd_ready,
      top->data_dma_ram_rd_resp_valid);

  DMAPorts p_dma_read_ctrl(top->m_axis_ctrl_dma_read_desc_dma_addr,
                           top->m_axis_ctrl_dma_read_desc_ram_sel,
                           top->m_axis_ctrl_dma_read_desc_ram_addr,
                           top->m_axis_ctrl_dma_read_desc_len,
                           top->m_axis_ctrl_dma_read_desc_tag,
                           top->m_axis_ctrl_dma_read_desc_valid,
                           top->m_axis_ctrl_dma_read_desc_ready,
                           top->s_axis_ctrl_dma_read_desc_status_tag,
                           top->s_axis_ctrl_dma_read_desc_status_valid);
  DMAPorts p_dma_write_ctrl(top->m_axis_ctrl_dma_write_desc_dma_addr,
                            top->m_axis_ctrl_dma_write_desc_ram_sel,
                            top->m_axis_ctrl_dma_write_desc_ram_addr,
                            top->m_axis_ctrl_dma_write_desc_len,
                            top->m_axis_ctrl_dma_write_desc_tag,
                            top->m_axis_ctrl_dma_write_desc_valid,
                            top->m_axis_ctrl_dma_write_desc_ready,
                            top->s_axis_ctrl_dma_write_desc_status_tag,
                            top->s_axis_ctrl_dma_write_desc_status_valid);
  DMAPorts p_dma_read_data(top->m_axis_data_dma_read_desc_dma_addr,
                           top->m_axis_data_dma_read_desc_ram_sel,
                           top->m_axis_data_dma_read_desc_ram_addr,
                           top->m_axis_data_dma_read_desc_len,
                           top->m_axis_data_dma_read_desc_tag,
                           top->m_axis_data_dma_read_desc_valid,
                           top->m_axis_data_dma_read_desc_ready,
                           top->s_axis_data_dma_read_desc_status_tag,
                           top->s_axis_data_dma_read_desc_status_valid);
  DMAPorts p_dma_write_data(top->m_axis_data_dma_write_desc_dma_addr,
                            top->m_axis_data_dma_write_desc_ram_sel,
                            top->m_axis_data_dma_write_desc_ram_addr,
                            top->m_axis_data_dma_write_desc_len,
                            top->m_axis_data_dma_write_desc_tag,
                            top->m_axis_data_dma_write_desc_valid,
                            top->m_axis_data_dma_write_desc_ready,
                            top->s_axis_data_dma_write_desc_status_tag,
                            top->s_axis_data_dma_write_desc_status_valid);

  // PCICoordinator pci_coord;
  PCICoordinator pci_coord_mmio;
  PCICoordinator pci_coord_msi;
  PCICoordinator pci_coord_rc;
  PCICoordinator pci_coord_wc;
  PCICoordinator pci_coord_rd;
  PCICoordinator pci_coord_wd;
  MMIOInterface mmio(*top, pci_coord_mmio);

  MemWriter mem_control_writer(p_mem_write_ctrl_dma);
  MemReader mem_control_reader(p_mem_read_ctrl_dma);
  MemWriter mem_data_writer(p_mem_write_data_dma);
  MemReader mem_data_reader(p_mem_read_data_dma);

  DMAReader dma_read_ctrl("read ctrl", p_dma_read_ctrl, mem_control_writer,
                          pci_coord_rc);
  DMAWriter dma_write_ctrl("write ctrl", p_dma_write_ctrl, mem_control_reader,
                           pci_coord_wc);
  DMAReader dma_read_data("read data", p_dma_read_data, mem_data_writer,
                          pci_coord_rd);
  DMAWriter dma_write_data("write data", p_dma_write_data, mem_data_reader,
                           pci_coord_wd);

  EthernetTx tx(*top);
  EthernetRx rx(*top);

  reset_inputs(top);
  top->rst = 1;
  top->eval();

  /* raising edge */
  top->clk = !top->clk;
  top->eval();

  top->rst = 0;

  while (!exiting) {
    while (nicsim_sync(&nsparams, main_time)) {
      std::cerr << "warn: nicsim_sync failed (t=" << main_time << ")"
                << std::endl;
    }
    nicsim_advance_epoch(&nsparams, main_time);

    do {
      poll_h2d(mmio);
      poll_n2d(rx);
    } while ((nsparams.sync_pci || nsparams.sync_eth) &&
             nicsim_next_timestamp(&nsparams) <= main_time && !exiting);

    /* falling edge */
    top->clk = !top->clk;
    main_time += clock_period / 2;
    top->eval();

    mmio.step();

    dma_read_ctrl.step();
    dma_write_ctrl.step();
    dma_read_data.step();
    dma_write_data.step();

    mem_control_writer.step();
    mem_control_reader.step();
    mem_data_writer.step();
    mem_data_reader.step();

    tx.step();
    rx.step();

    msi_step(*top, pci_coord_msi);

    /* raising edge */
    top->clk = !top->clk;
    main_time += clock_period / 2;

    // top->s_axis_tx_ptp_ts_96 = main_time;
    top->s_axis_tx_ptp_ts_valid = 1;
    top->s_axis_rx_ptp_ts_valid = 1;

    top->eval();
  }
  report_outputs(top);
  std::cout << std::endl << std::endl << "main_time:" << main_time << std::endl;

#ifdef TRACE_ENABLED
  trace->dump(main_time + 1);
  trace->close();
#endif
  top->final();
  delete top;
  return 0;
}
