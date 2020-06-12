#include <iostream>
#include <deque>
#include <set>
#include <signal.h>

extern "C" {
    #include <nicsim.h>
}

#include "Vinterface.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

#include "corundum.h"
#include "dma.h"
#include "mem.h"

#define CLOCK_PERIOD (10 * 1000 * 1000ULL) // 200KHz
#define PCI_ASYNCHRONY (500 * 1000 * 1000ULL) // 200us
#define ETH_ASYNCHRONY (500 * 1000 * 1000ULL) // 200us

struct DMAOp;

static volatile int exiting = 0;
static uint64_t main_time = 0;
static uint64_t pci_last_time = 0;
static uint64_t eth_last_time = 0;
//static VerilatedVcdC* trace;



static void sigint_handler(int dummy)
{
    exiting = 1;
}

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
                    delete rCur;
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
                    delete wCur;
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

            //std::cout << "read complete addr=" << op.addr << " val=" << op.value << std::endl;
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
            volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
            volatile struct cosim_pcie_proto_d2h_writecomp *rc;

            if (!msg)
                throw "completion alloc failed";

            rc = &msg->writecomp;
            rc->req_id = op.id;

            //WMB();
            rc->own_type = COSIM_PCIE_PROTO_D2H_MSG_WRITECOMP |
                COSIM_PCIE_PROTO_D2H_OWN_HOST;

            //std::cout << "write complete addr=" << op.addr << " val=" << op.value << std::endl;
        }

};

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

void pci_dma_issue(DMAOp *op)
{
    volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
    uint8_t ty;

    if (!msg)
        throw "completion alloc failed";

    if (op->write) {
        volatile struct cosim_pcie_proto_d2h_write *write = &msg->write;
        write->req_id = (uintptr_t) op;
        write->offset = op->dma_addr;
        write->len = op->len;

        // TODO: check DMA length
        memcpy((void *) write->data, op->data, op->len);

        // WMB();
        write->own_type = COSIM_PCIE_PROTO_D2H_MSG_WRITE |
            COSIM_PCIE_PROTO_D2H_OWN_HOST;
    } else {
        volatile struct cosim_pcie_proto_d2h_read *read = &msg->read;
        read->req_id = (uintptr_t) op;
        read->offset = op->dma_addr;
        read->len = op->len;

        // WMB();
        read->own_type = COSIM_PCIE_PROTO_D2H_MSG_READ |
            COSIM_PCIE_PROTO_D2H_OWN_HOST;
    }

    pci_dma_pending.insert(op);
}

static void h2d_readcomp(volatile struct cosim_pcie_proto_h2d_readcomp *rc)
{
    DMAOp *op = (DMAOp *) (uintptr_t) rc->req_id;
    if (pci_dma_pending.find(op) == pci_dma_pending.end())
        throw "unexpected completion";
    pci_dma_pending.erase(op);

    memcpy(op->data, (void *) rc->data, op->len);

#if 0
    std::cerr << "dma read comp: ";
    for (size_t i = 0; i < op->len; i++)
        std::cerr << (unsigned) op->data[i] << " ";
    std::cerr << std::endl;
#endif


    op->engine->pci_op_complete(op);
}

static void h2d_writecomp(volatile struct cosim_pcie_proto_h2d_writecomp *wc)
{
    DMAOp *op = (DMAOp *) (uintptr_t) wc->req_id;
    if (pci_dma_pending.find(op) == pci_dma_pending.end())
        throw "unexpected completion";
    pci_dma_pending.erase(op);

    op->engine->pci_op_complete(op);
}

static uint64_t csr_read(uint64_t off)
{
    switch (off) {
        case   0x00: return 32; /* firmware id */
        case   0x04: return 1; /* firmware version */
        case   0x08: return 0x43215678; /* board id */
        case   0x0c: return 0x1; /* board version */
        case   0x10: return 1; /* phc count */
        case   0x14: return 0x200; /* phc offset */
        case   0x18: return 0x80; /* phc stride */
        case   0x20: return 1; /* if_count */
        case   0x24: return 0x80000; /* if stride */
        case   0x2c: return 0x80000; /* if csr offset */
        case  0x200: return 0x1; /* phc features */
        default:
            std::cerr << "csr_read(" << off << ") unimplemented" << std::endl;
            return 0;
    }
}

static void csr_write(uint64_t off, uint64_t val)
{
}

static void h2d_read(MMIOInterface &mmio,
        volatile struct cosim_pcie_proto_h2d_read *read)
{
    //std::cout << "got read " << read->offset << std::endl;
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

static void h2d_write(MMIOInterface &mmio,
        volatile struct cosim_pcie_proto_h2d_write *write)
{
    uint64_t val = 0;

    memcpy(&val, (void *) write->data, write->len);

    //std::cout << "got write " << write->offset << " = " << val << std::endl;

    if (write->offset < 0x80000) {
        volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
        volatile struct cosim_pcie_proto_d2h_writecomp *wc;

        if (!msg)
            throw "completion alloc failed";

        csr_write(write->offset, val);

        wc = &msg->writecomp;
        wc->req_id = write->req_id;

        //WMB();
        wc->own_type = COSIM_PCIE_PROTO_D2H_MSG_WRITECOMP |
            COSIM_PCIE_PROTO_D2H_OWN_HOST;
    } else {
        mmio.issueWrite(write->req_id, write->offset, write->len, val);
    }
}

static void h2d_sync(volatile struct cosim_pcie_proto_h2d_sync *sync)
{
    pci_last_time = sync->timestamp;
}

static void poll_h2d(MMIOInterface &mmio)
{
    volatile union cosim_pcie_proto_h2d *msg = nicif_h2d_poll();
    uint8_t t;

    if (msg == NULL)
        return;

    t = msg->dummy.own_type & COSIM_PCIE_PROTO_H2D_MSG_MASK;
    //std::cerr << "poll_h2d: polled type=" << (int) t << std::endl;
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

        case COSIM_PCIE_PROTO_H2D_MSG_SYNC:
            h2d_sync(&msg->sync);
            break;

        default:
            std::cerr << "poll_h2d: unsupported type=" << t << std::endl;
    }

    nicif_h2d_done(msg);
    nicif_h2d_next();

};

class EthernetTx {
    protected:
        Vinterface &top;
        uint8_t packet_buf[2048];
        size_t packet_len;

    public:
        EthernetTx(Vinterface &top_)
            : top(top_), packet_len(0)
        {
        }

        void packet_done()
        {
            volatile union cosim_eth_proto_d2n *msg = nicsim_d2n_alloc();
            volatile struct cosim_eth_proto_d2n_send *send;

            if (!msg)
                throw "completion alloc failed";

            send = &msg->send;
            memcpy((void *) send->data, packet_buf, packet_len);
            send->len = packet_len;

            //WMB();
            send->own_type = COSIM_ETH_PROTO_D2N_MSG_SEND |
                COSIM_ETH_PROTO_D2N_OWN_NET;

            std::cerr << "EthernetTx: packet len=" << std::hex << packet_len << " ";
            for (size_t i = 0; i < packet_len; i++) {
                std::cerr << (unsigned) packet_buf[i] << " ";
            }
            std::cerr << std::endl;
        }

        void step()
        {
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
        uint8_t packet_buf[2048];
        size_t packet_len;
        size_t packet_off;

    public:
        EthernetRx(Vinterface &top_)
            : top(top_), packet_len(0), packet_off(0)
        {
        }

        void packet_received(const void *data, size_t len)
        {
            if (packet_len != 0) {
                std::cerr << "EthernetRx: dropping packet" << std::endl;
                return;
            }

            packet_off = 0;
            packet_len = len;
            memcpy(packet_buf, data, len);

            std::cerr << "EthernetRx: packet len=" << std::hex << packet_len << " ";
            for (size_t i = 0; i < packet_len; i++) {
                std::cerr << (unsigned) packet_buf[i] << " ";
            }
            std::cerr << std::endl;
        }

        void step()
        {
            if (packet_len != 0) {
                // we have data to send
                if (packet_off != 0 && !top.rx_axis_tready) {
                    // no ready signal, can't advance
                } else if (packet_off == packet_len) {
                    // done with packet
                    std::cerr << "EthernetRx: finished packet" << std::endl;
                    top.rx_axis_tvalid = 0;
                    top.rx_axis_tlast = 0;
                    packet_off = packet_len = 0;
                } else {
                    // put out more packet data
                    std::cerr << "EthernetRx: push flit " << packet_off << std::endl;
                    top.rx_axis_tkeep = 0;
                    top.rx_axis_tdata = 0;
                    for (size_t i = 0; i < 8 && packet_off < packet_len; i++) {
                        top.rx_axis_tdata |=
                            ((uint64_t) packet_buf[packet_off]) << (i * 8);
                        top.rx_axis_tkeep |= (1 << i);
                        packet_off++;
                    }
                    top.rx_axis_tvalid = 1;
                    top.rx_axis_tlast = (packet_off == packet_len);
                }
                //trace->dump(main_time);
            } else {
                // no data
                top.rx_axis_tvalid = 0;
                top.rx_axis_tlast = 0;
            }
        }

};

static void n2d_recv(EthernetRx &rx,
        volatile struct cosim_eth_proto_n2d_recv *recv)
{
    rx.packet_received((const void *) recv->data, recv->len);
}

static void poll_n2d(EthernetRx &rx)
{
    volatile union cosim_eth_proto_n2d *msg = nicif_n2d_poll();
    uint8_t t;

    if (msg == NULL)
        return;

    t = msg->dummy.own_type & COSIM_ETH_PROTO_N2D_MSG_MASK;
    switch (t) {
        case COSIM_ETH_PROTO_N2D_MSG_RECV:
            n2d_recv(rx, &msg->recv);
            break;

        default:
            std::cerr << "poll_n2d: unsupported type=" << t << std::endl;
    }

    nicif_n2d_done(msg);
    nicif_n2d_next();
}

static void msi_issue(uint8_t vec)
{
    volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
    volatile struct cosim_pcie_proto_d2h_interrupt *intr;

    std::cerr << "MSI interrupt vec=" << (int) vec << std::endl;

    intr = &msg->interrupt;
    intr->vector = vec;
    intr->inttype = COSIM_PCIE_PROTO_INT_MSI;

    // WMB();
    intr->own_type = COSIM_PCIE_PROTO_D2H_MSG_INTERRUPT |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;
}

static void msi_step(Vinterface &top)
{
    if (!top.msi_irq)
        return;

    for (size_t i = 0; i < 32; i++) {
        if (!((1ULL << i) & top.msi_irq))
            continue;

        msi_issue(i);
    }
}

static void sync_pci(MMIOInterface &mmio)
{
    uint64_t cur_ts = (main_time / 2) * CLOCK_PERIOD;
    volatile union cosim_pcie_proto_d2h *msg = nicsim_d2h_alloc();
    volatile struct cosim_pcie_proto_d2h_sync *sync;

    sync = &msg->sync;

    sync->timestamp = cur_ts + PCI_ASYNCHRONY;
    // WMB();
    sync->own_type = COSIM_PCIE_PROTO_D2H_MSG_SYNC |
        COSIM_PCIE_PROTO_D2H_OWN_HOST;

    while (pci_last_time < cur_ts && !exiting) {
        /*std::cout << "waiting for pci pci_time=" << pci_last_time <<
            "  cur=" << cur_ts << std::endl;*/
        poll_h2d(mmio);
    }
}

static void sync_eth(EthernetRx &rx)
{
}

int main(int argc, char *argv[])
{
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    int sync_pci_en, sync_eth_en;
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

    sync_pci_en = 1;
    sync_eth_en = 1;
    if (nicsim_init(&di, "/tmp/cosim-pci", &sync_pci_en,
                "/tmp/cosim-eth", &sync_eth_en, "/dev/shm/dummy_nic_shm"))
    {
        return EXIT_FAILURE;
    }
    std::cout << "sync_pci=" << sync_pci_en << "  sync_eth=" << sync_eth_en <<
        std::endl;

    signal(SIGINT, sigint_handler);


    Vinterface *top = new Vinterface;
    /*trace = new VerilatedVcdC;
    top->trace(trace, 99);
    trace->open("debug.vcd");*/

    MemWritePort p_mem_write_ctrl_dma(
            top->ctrl_dma_ram_wr_cmd_sel,
            top->ctrl_dma_ram_wr_cmd_be,
            top->ctrl_dma_ram_wr_cmd_addr,
            top->ctrl_dma_ram_wr_cmd_data,
            top->ctrl_dma_ram_wr_cmd_valid,
            top->ctrl_dma_ram_wr_cmd_ready);
    MemReadPort p_mem_read_ctrl_dma(
            top->ctrl_dma_ram_rd_cmd_sel,
            top->ctrl_dma_ram_rd_cmd_addr,
            top->ctrl_dma_ram_rd_cmd_valid,
            top->ctrl_dma_ram_rd_resp_ready,
            top->ctrl_dma_ram_rd_resp_data,
            top->ctrl_dma_ram_rd_cmd_ready,
            top->ctrl_dma_ram_rd_resp_valid);
    MemWritePort p_mem_write_data_dma(
            top->data_dma_ram_wr_cmd_sel,
            top->data_dma_ram_wr_cmd_be,
            top->data_dma_ram_wr_cmd_addr,
            top->data_dma_ram_wr_cmd_data,
            top->data_dma_ram_wr_cmd_valid,
            top->data_dma_ram_wr_cmd_ready);
    MemReadPort p_mem_read_data_dma(
            top->data_dma_ram_rd_cmd_sel,
            top->data_dma_ram_rd_cmd_addr,
            top->data_dma_ram_rd_cmd_valid,
            top->data_dma_ram_rd_resp_ready,
            top->data_dma_ram_rd_resp_data,
            top->data_dma_ram_rd_cmd_ready,
            top->data_dma_ram_rd_resp_valid);

    DMAPorts p_dma_read_ctrl(
            top->m_axis_ctrl_dma_read_desc_dma_addr,
            top->m_axis_ctrl_dma_read_desc_ram_sel,
            top->m_axis_ctrl_dma_read_desc_ram_addr,
            top->m_axis_ctrl_dma_read_desc_len,
            top->m_axis_ctrl_dma_read_desc_tag,
            top->m_axis_ctrl_dma_read_desc_valid,
            top->m_axis_ctrl_dma_read_desc_ready,
            top->s_axis_ctrl_dma_read_desc_status_tag,
            top->s_axis_ctrl_dma_read_desc_status_valid);
    DMAPorts p_dma_write_ctrl(
            top->m_axis_ctrl_dma_write_desc_dma_addr,
            top->m_axis_ctrl_dma_write_desc_ram_sel,
            top->m_axis_ctrl_dma_write_desc_ram_addr,
            top->m_axis_ctrl_dma_write_desc_len,
            top->m_axis_ctrl_dma_write_desc_tag,
            top->m_axis_ctrl_dma_write_desc_valid,
            top->m_axis_ctrl_dma_write_desc_ready,
            top->s_axis_ctrl_dma_write_desc_status_tag,
            top->s_axis_ctrl_dma_write_desc_status_valid);
    DMAPorts p_dma_read_data(
            top->m_axis_data_dma_read_desc_dma_addr,
            top->m_axis_data_dma_read_desc_ram_sel,
            top->m_axis_data_dma_read_desc_ram_addr,
            top->m_axis_data_dma_read_desc_len,
            top->m_axis_data_dma_read_desc_tag,
            top->m_axis_data_dma_read_desc_valid,
            top->m_axis_data_dma_read_desc_ready,
            top->s_axis_data_dma_read_desc_status_tag,
            top->s_axis_data_dma_read_desc_status_valid);
    DMAPorts p_dma_write_data(
            top->m_axis_data_dma_write_desc_dma_addr,
            top->m_axis_data_dma_write_desc_ram_sel,
            top->m_axis_data_dma_write_desc_ram_addr,
            top->m_axis_data_dma_write_desc_len,
            top->m_axis_data_dma_write_desc_tag,
            top->m_axis_data_dma_write_desc_valid,
            top->m_axis_data_dma_write_desc_ready,
            top->s_axis_data_dma_write_desc_status_tag,
            top->s_axis_data_dma_write_desc_status_valid);


    MMIOInterface mmio(*top);

    MemWriter mem_control_writer(p_mem_write_ctrl_dma);
    MemReader mem_control_reader(p_mem_read_ctrl_dma);
    MemWriter mem_data_writer(p_mem_write_data_dma);
    MemReader mem_data_reader(p_mem_read_data_dma);

    DMAReader dma_read_ctrl("read ctrl", p_dma_read_ctrl, mem_control_writer);
    DMAWriter dma_write_ctrl("write ctrl", p_dma_write_ctrl, mem_control_reader);
    DMAReader dma_read_data("read data", p_dma_read_data, mem_data_writer);
    DMAWriter dma_write_data("write data", p_dma_write_data, mem_data_reader);

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
        if (sync_pci_en)
            sync_pci(mmio);
        if (sync_eth_en)
            sync_eth(rx);
        poll_h2d(mmio);
        poll_n2d(rx);

        /* falling edge */
        top->clk = !top->clk;
        main_time++;
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

        msi_step(*top);

        /* raising edge */
        top->clk = !top->clk;
        main_time++;

        //top->s_axis_tx_ptp_ts_96 = main_time;
        top->s_axis_tx_ptp_ts_valid = 1;
        top->s_axis_rx_ptp_ts_valid = 1;

        top->eval();
    }
    report_outputs(top);

    //trace->close();
    top->final();
    delete top;
    return 0;
}
