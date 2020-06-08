#include <iostream>
#include <deque>

extern "C" {
    #include <nicsim.h>
}

#include "Vinterface.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

static uint64_t main_time = 0;

double sc_time_stamp()
{
    return main_time;
}

static void reset_inputs(Vinterface *top)
{
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
    //top->ctrl_dma_ram_wr_cmd_be = 0;
    //top->ctrl_dma_ram_wr_cmd_addr = 0;
    top->ctrl_dma_ram_wr_cmd_valid = 0;
    top->ctrl_dma_ram_rd_cmd_sel = 0;
    //top->ctrl_dma_ram_rd_cmd_addr = 0;
    top->ctrl_dma_ram_rd_cmd_valid = 0;
    top->ctrl_dma_ram_rd_resp_ready = 0;
    top->data_dma_ram_wr_cmd_sel = 0;
    //top->data_dma_ram_wr_cmd_be = 0;
    //top->data_dma_ram_wr_cmd_addr = 0;
    top->data_dma_ram_wr_cmd_valid = 0;
    top->data_dma_ram_rd_cmd_sel = 0;
    //top->data_dma_ram_rd_cmd_addr = 0;
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

static void report_output(const char *label, uint64_t val)
{
    if (val == 0)
        return;

    std::cout << "    " << label << " = " << val << std::endl;
}

static void report_outputs(Vinterface *top)
{
    report_output("m_axis_ctrl_dma_read_desc_dma_addr", top->m_axis_ctrl_dma_read_desc_dma_addr);
    report_output("m_axis_ctrl_dma_read_desc_ram_sel", top->m_axis_ctrl_dma_read_desc_ram_sel);
    report_output("m_axis_ctrl_dma_read_desc_ram_addr", top->m_axis_ctrl_dma_read_desc_ram_addr);
    report_output("m_axis_ctrl_dma_read_desc_len", top->m_axis_ctrl_dma_read_desc_len);
    report_output("m_axis_ctrl_dma_read_desc_tag", top->m_axis_ctrl_dma_read_desc_tag);
    report_output("m_axis_ctrl_dma_read_desc_valid", top->m_axis_ctrl_dma_read_desc_valid);
    report_output("m_axis_ctrl_dma_write_desc_dma_addr", top->m_axis_ctrl_dma_write_desc_dma_addr);
    report_output("m_axis_ctrl_dma_write_desc_ram_sel", top->m_axis_ctrl_dma_write_desc_ram_sel);
    report_output("m_axis_ctrl_dma_write_desc_ram_addr", top->m_axis_ctrl_dma_write_desc_ram_addr);
    report_output("m_axis_ctrl_dma_write_desc_len", top->m_axis_ctrl_dma_write_desc_len);
    report_output("m_axis_ctrl_dma_write_desc_tag", top->m_axis_ctrl_dma_write_desc_tag);
    report_output("m_axis_ctrl_dma_write_desc_valid", top->m_axis_ctrl_dma_write_desc_valid);
    report_output("m_axis_data_dma_read_desc_dma_addr", top->m_axis_data_dma_read_desc_dma_addr);
    report_output("m_axis_data_dma_read_desc_ram_sel", top->m_axis_data_dma_read_desc_ram_sel);
    report_output("m_axis_data_dma_read_desc_ram_addr", top->m_axis_data_dma_read_desc_ram_addr);
    report_output("m_axis_data_dma_read_desc_len", top->m_axis_data_dma_read_desc_len);
    report_output("m_axis_data_dma_read_desc_tag", top->m_axis_data_dma_read_desc_tag);
    report_output("m_axis_data_dma_read_desc_valid", top->m_axis_data_dma_read_desc_valid);
    report_output("m_axis_data_dma_write_desc_dma_addr", top->m_axis_data_dma_write_desc_dma_addr);
    report_output("m_axis_data_dma_write_desc_ram_sel", top->m_axis_data_dma_write_desc_ram_sel);
    report_output("m_axis_data_dma_write_desc_ram_addr", top->m_axis_data_dma_write_desc_ram_addr);
    report_output("m_axis_data_dma_write_desc_len", top->m_axis_data_dma_write_desc_len);
    report_output("m_axis_data_dma_write_desc_tag", top->m_axis_data_dma_write_desc_tag);
    report_output("m_axis_data_dma_write_desc_valid", top->m_axis_data_dma_write_desc_valid);
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

class MMIOInterface {
    protected:
        struct Op {
            uint64_t id;
            uint64_t addr;
            uint64_t value;
            size_t len;
            bool isWrite;
        };

        enum OpState {
            AddrIssued,
            AddrAcked,
            AddrDone,
        };

        Vinterface &top;
        std::deque<Op *> queue;
        Op *rCur, *wCur;
        enum OpState rState, wState;

    public:
        MMIOInterface(Vinterface &top_)
            : top(top_), rCur(0), wCur(0)
        {
        }

        void step()
        {
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
                    completeRead(*rCur);
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
                    completeWrite(*wCur, top.s_axil_bresp);
                    wCur = 0;
                }
            } else if (/*!top.clk &&*/ !queue.empty()) {
                /* issue new operation */

                Op *op = queue.front();
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

        void issueRead(uint64_t id, uint64_t addr, size_t len)
        {
            Op *op = new Op;
            op->id = id;
            op->addr = addr;
            op->len = len;
            op->isWrite = false;
            queue.push_back(op);
        }

        void completeRead(Op &op)
        {
            volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
            volatile struct cosim_pcie_proto_d2h_readcomp *rc;

            if (!msg)
                throw "completion alloc failed";

            rc = &msg->readcomp;
            memcpy((void *) rc->data, &op.value, op.len);
            rc->req_id = op.id;

            //WMB();
            rc->own_type = COSIM_PCIE_PROTO_D2H_MSG_READCOMP |
                COSIM_PCIE_PROTO_D2H_OWN_HOST;

            std::cout << "read complete addr=" << op.addr << " val=" << op.value << std::endl;
        }


        void issueWrite(uint64_t id, uint64_t addr, size_t len, uint64_t val)
        {
            Op *op = new Op;
            op->id = id;
            op->addr = addr;
            op->len = len;
            op->value = val;
            op->isWrite = true;
            queue.push_back(op);
        }

        void completeWrite(Op &op, uint8_t status)
        {
            std::cout << "write complete addr=" << op.addr << " val=" << op.value << std::endl;
        }

};

static uint64_t csr_read(uint64_t off)
{
    switch (off) {
        case 0x00: return 32; /* firmware id */
        case 0x04: return 1; /* firmware version */
        case 0x08: return 0x43215678; /* board id */
        case 0x0c: return 0x1; /* board version */
        case 0x10: return 1; /* phc count */
        case 0x14: return 0x200; /* phc offset */
        case 0x18: return 0x80; /* phc stride */
        case 0x20: return 1; /* if_count */
        case 0x24: return 0x80000; /* if stride */
        case 0x2c: return 0x80000; /* if csr offset */
        default:
            std::cerr << "csr_read(" << off << ") unimplemented" << std::endl;
            return 0;
    }
}

static void h2d_read(MMIOInterface &mmio,
        volatile struct cosim_pcie_proto_h2d_read *read)
{
    std::cout << "got read " << read->offset << std::endl;
    if (read->offset < 0x80000) {
        volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
        volatile struct cosim_pcie_proto_d2h_readcomp *rc;

        if (!msg)
            throw "completion alloc failed";

        rc = &msg->readcomp;
        memset((void *) rc->data, 0, read->len);
        uint64_t val = csr_read(read->offset);
        memcpy((void *) rc->data, &val, read->len);
        rc->req_id = read->req_id;

        //WMB();
        rc->own_type = COSIM_PCIE_PROTO_D2H_MSG_READCOMP |
            COSIM_PCIE_PROTO_D2H_OWN_HOST;
    } else {
        /*printf("read(bar=%u, off=%lu, len=%u) = %lu\n", read->bar, read->offset,
                read->len, val);*/
        mmio.issueRead(read->req_id, read->offset, read->len);
    }
}


static void poll_h2d(MMIOInterface &mmio)
{
    volatile union cosim_pcie_proto_h2d *msg = nicif_h2d_poll();
    uint8_t t;

    if (msg == NULL)
        return;

    t = msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_MSG_MASK;
    std::cerr << "poll_h2d: polled type=" << t << std::endl;
    switch (t) {
        case COSIM_PCIE_PROTO_H2D_MSG_READ:
            h2d_read(mmio, &msg->read);
            break;

        /*case COSIM_PCIE_PROTO_H2D_MSG_WRITE:
            h2d_write(&msg->write);
            break;*/

        default:
            std::cerr << "poll_h2d: unsupported type=" << t << std::endl;
    }

    nicif_h2d_done(msg);
    nicif_h2d_next();

}

int main(int argc, char *argv[])
{
    Verilated::commandArgs(argc, argv);
    //Verilated::traceEverOn(true);

    struct cosim_pcie_proto_dev_intro di;
    memset(&di, 0, sizeof(di));

    di.bars[0].len = 1 << 24;
    di.bars[0].flags = COSIM_PCIE_PROTO_BAR_64;

    /*di.bars[2].len = 1024;
    di.bars[2].flags = COSIM_PCIE_PROTO_BAR_IO;*/

    di.pci_vendor_id = 0x5543;
    di.pci_device_id = 0x1001;
    di.pci_class = 0x02;
    di.pci_subclass = 0x00;
    di.pci_revision = 0x00;

    if (nicsim_init(&di, "/tmp/cosim-pci", "/dev/shm/dummy_nic_shm")) {
        return EXIT_FAILURE;
    }



    Vinterface *top = new Vinterface;

    VerilatedVcdC *tr = 0;
    /*VerilatedVcdC *tr = new VerilatedVcdC;
    top->trace(tr, 1000);
    tr->open("debug.vcd");*/
    // size: bar 0: 24 bits

    MMIOInterface mmio(*top);

    reset_inputs(top);
    top->rst = 1;

    top->eval();
    /*std::cout << "0 low:" << std::endl;
    report_outputs(top);*/

    if (tr)
        tr->dump(0);

    top->clk = !top->clk;
    top->eval();
    /*std::cout << "0 high:" << std::endl;
    report_outputs(top);*/

    if (tr)
        tr->dump(1);

    top->rst = 0;

    while (1) {
        poll_h2d(mmio);

        top->clk = !top->clk;

        top->eval();
        /*std::cout << (i + 2) << " low:" << std::endl;
        report_outputs(top);*/

        /*tr->dump(2 + i * 2);*/

        mmio.step();
        top->clk = !top->clk;

        top->eval();
        /*std::cout << (i + 2) << " high:" << std::endl;
        report_outputs(top);*/

        /*tr->dump(3 + i * 2);*/
    }
    report_outputs(top);

    if (tr)
        tr->close();
    top->final();
    delete top;
    return 0;
}
