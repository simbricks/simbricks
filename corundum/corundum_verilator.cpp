#include <iostream>

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

int main(int argc, char *argv[])
{
    Verilated::commandArgs(argc, argv);
    Vinterface *top = new Vinterface;

    // size: bar 0: 24 bits

    reset_inputs(top);
    top->rst = 1;

    top->eval();
    std::cout << "0 low:" << std::endl;
    report_outputs(top);

    top->clk = !top->clk;
    top->eval();
    std::cout << "0 high:" << std::endl;
    report_outputs(top);

    top->rst = 0;
    top->clk = !top->clk;
    top->eval();
    std::cout << "1 low:" << std::endl;
    report_outputs(top);

    top->clk = !top->clk;
    top->eval();
    std::cout << "1 high:" << std::endl;
    report_outputs(top);


    top->final();
    delete top;
    return 0;
}
