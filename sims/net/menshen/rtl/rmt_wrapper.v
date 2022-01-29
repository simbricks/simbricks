`timescale 1ns / 1ps

module rmt_wrapper #(
	// AXI-Lite parameters
	// Width of AXI lite data bus in bits
    parameter AXIL_DATA_WIDTH = 32,
    // Width of AXI lite address bus in bits
    parameter AXIL_ADDR_WIDTH = 16,
    // Width of AXI lite wstrb (width of data bus in words)
    parameter AXIL_STRB_WIDTH = (AXIL_DATA_WIDTH/8),
	// AXI Stream parameters
	// Slave
	parameter C_S_AXIS_DATA_WIDTH = 512,
	parameter C_S_AXIS_TUSER_WIDTH = 128,
	// Master
	// self-defined
    parameter PHV_LEN = 48*8+32*8+16*8+256,
    parameter KEY_LEN = 48*2+32*2+16*2+1,
    parameter ACT_LEN = 25,
    parameter KEY_OFF = 6*3+20,
	parameter C_NUM_QUEUES = 4,
	parameter C_VLANID_WIDTH = 12
)
(
	input										clk,		// axis clk
	input										aresetn,	
	input [31:0]								vlan_drop_flags,
	output reg [31:0]								ctrl_token,

	/*
     * input Slave AXI Stream
     */
	input [C_S_AXIS_DATA_WIDTH-1:0]				s_axis_tdata,
	input [((C_S_AXIS_DATA_WIDTH/8))-1:0]		s_axis_tkeep,
	input [C_S_AXIS_TUSER_WIDTH-1:0]			s_axis_tuser,
	input										s_axis_tvalid,
	output										s_axis_tready,
	input										s_axis_tlast,

	/*
     * output Master AXI Stream
     */
	output     [C_S_AXIS_DATA_WIDTH-1:0]		m_axis_tdata,
	output     [((C_S_AXIS_DATA_WIDTH/8))-1:0]	m_axis_tkeep,
	output     [C_S_AXIS_TUSER_WIDTH-1:0]		m_axis_tuser,
	output    									m_axis_tvalid,
	input										m_axis_tready,
	output  									m_axis_tlast

	
);

reg [31:0] vlan_drop_flags_r;
wire [31:0] ctrl_token_r;

always @(posedge clk) begin
	if (~aresetn) begin
		vlan_drop_flags_r <= 0;
		ctrl_token <= 0;
	end
	else begin
		vlan_drop_flags_r <= vlan_drop_flags;
		ctrl_token <= ctrl_token_r;
	end
end

integer idx;

/*=================================================*/
localparam PKT_VEC_WIDTH = (6+4+2)*8*8+256;

wire								stg0_phv_in_valid;
wire [PKT_VEC_WIDTH-1:0]			stg0_phv_in;
// stage-related
wire [PKT_VEC_WIDTH-1:0]			stg0_phv_out;
wire								stg0_phv_out_valid;
wire [PKT_VEC_WIDTH-1:0]			stg1_phv_out;
wire								stg1_phv_out_valid;
wire [PKT_VEC_WIDTH-1:0]			stg2_phv_out;
wire								stg2_phv_out_valid;
wire [PKT_VEC_WIDTH-1:0]			stg3_phv_out;
wire								stg3_phv_out_valid;
// wire [PKT_VEC_WIDTH-1:0]			stg4_phv_out;
// wire								stg4_phv_out_valid;

reg [PKT_VEC_WIDTH-1:0]				stg0_phv_in_d1;
reg [PKT_VEC_WIDTH-1:0]				stg0_phv_out_d1;
reg [PKT_VEC_WIDTH-1:0]				stg1_phv_out_d1;
reg [PKT_VEC_WIDTH-1:0]				stg2_phv_out_d1;
reg [PKT_VEC_WIDTH-1:0]				stg3_phv_out_d1;

reg									stg0_phv_in_valid_d1;
reg									stg0_phv_out_valid_d1;
reg									stg1_phv_out_valid_d1;
reg									stg2_phv_out_valid_d1;
reg									stg3_phv_out_valid_d1;


//
wire [C_VLANID_WIDTH-1:0]			stg0_vlan_in;
wire								stg0_vlan_valid_in;
reg [C_VLANID_WIDTH-1:0]			stg0_vlan_in_r;
reg									stg0_vlan_valid_in_r;

wire								stg0_vlan_ready;
wire [C_VLANID_WIDTH-1:0]			stg0_vlan_out;
wire								stg0_vlan_valid_out;
reg [C_VLANID_WIDTH-1:0]			stg0_vlan_out_r;
reg									stg0_vlan_valid_out_r;

wire								stg1_vlan_ready;
wire [C_VLANID_WIDTH-1:0]			stg1_vlan_out;
wire								stg1_vlan_valid_out;
reg [C_VLANID_WIDTH-1:0]			stg1_vlan_out_r;
reg									stg1_vlan_valid_out_r;

wire								stg2_vlan_ready;
wire [C_VLANID_WIDTH-1:0]			stg2_vlan_out;
wire								stg2_vlan_valid_out;
reg [C_VLANID_WIDTH-1:0]			stg2_vlan_out_r;
reg 								stg2_vlan_valid_out_r;

wire								stg3_vlan_ready;
wire [C_VLANID_WIDTH-1:0]			stg3_vlan_out;
wire								stg3_vlan_valid_out;
reg [C_VLANID_WIDTH-1:0]			stg3_vlan_out_r;
reg 								stg3_vlan_valid_out_r;

wire								last_stg_vlan_ready;

// back pressure signals
wire s_axis_tready_p;
wire stg0_ready;
wire stg1_ready;
wire stg2_ready;
wire stg3_ready;
wire last_stg_ready;


/*=================================================*/

wire [C_VLANID_WIDTH-1:0]					s_vlan_id;
wire										s_vlan_id_valid;

reg [C_VLANID_WIDTH-1:0]					s_vlan_id_r;
reg 										s_vlan_id_valid_r;

//NOTE: to filter out packets other than UDP/IP.
wire [C_S_AXIS_DATA_WIDTH-1:0]				s_axis_tdata_f;
wire [((C_S_AXIS_DATA_WIDTH/8))-1:0]		s_axis_tkeep_f;
wire [C_S_AXIS_TUSER_WIDTH-1:0]				s_axis_tuser_f;
wire										s_axis_tvalid_f;
wire										s_axis_tready_f;
wire										s_axis_tlast_f;

reg [C_S_AXIS_DATA_WIDTH-1:0]			s_axis_tdata_f_reg;
reg [((C_S_AXIS_DATA_WIDTH/8))-1:0]		s_axis_tkeep_f_reg;
reg [C_S_AXIS_TUSER_WIDTH-1:0]			s_axis_tuser_f_reg;
reg										s_axis_tvalid_f_reg;
reg										s_axis_tlast_f_reg;

//NOTE: filter control packets from data packets.
wire [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_1;
wire [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_1;
wire [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_1;
wire										ctrl_s_axis_tvalid_1;
wire										ctrl_s_axis_tlast_1;

reg  [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_1_r;
reg  [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_1_r;
reg  [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_1_r;
reg 										ctrl_s_axis_tvalid_1_r;
reg 										ctrl_s_axis_tlast_1_r;

pkt_filter #(
	.C_S_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
	.C_S_AXIS_TUSER_WIDTH(C_S_AXIS_TUSER_WIDTH)
)pkt_filter
(
	.clk(clk),
	.aresetn(aresetn),

	.vlan_drop_flags(vlan_drop_flags_r),
	.ctrl_token(ctrl_token_r),

	// input Slave AXI Stream
	.s_axis_tdata(s_axis_tdata),
	.s_axis_tkeep(s_axis_tkeep),
	.s_axis_tuser(s_axis_tuser),
	.s_axis_tvalid(s_axis_tvalid),
	.s_axis_tready(s_axis_tready),
	.s_axis_tlast(s_axis_tlast),

	.vlan_id(s_vlan_id),
	.vlan_id_valid(s_vlan_id_valid),

	// output Master AXI Stream
	.m_axis_tdata(s_axis_tdata_f),
	.m_axis_tkeep(s_axis_tkeep_f),
	.m_axis_tuser(s_axis_tuser_f),
	.m_axis_tvalid(s_axis_tvalid_f),
	// .m_axis_tready(s_axis_tready_f && s_axis_tready_p),
	.m_axis_tready(s_axis_tready_p),
	.m_axis_tlast(s_axis_tlast_f),

	//control path
	.c_m_axis_tdata(ctrl_s_axis_tdata_1),
	.c_m_axis_tkeep(ctrl_s_axis_tkeep_1),
	.c_m_axis_tuser(ctrl_s_axis_tuser_1),
	.c_m_axis_tvalid(ctrl_s_axis_tvalid_1),
	.c_m_axis_tlast(ctrl_s_axis_tlast_1)
);

// we will have multiple pkt fifos and phv fifos
// pkt fifo wires
wire [C_S_AXIS_DATA_WIDTH-1:0]		pkt_fifo_tdata_out [C_NUM_QUEUES-1:0];
wire [C_S_AXIS_TUSER_WIDTH-1:0]		pkt_fifo_tuser_out [C_NUM_QUEUES-1:0];
wire [C_S_AXIS_DATA_WIDTH/8-1:0]	pkt_fifo_tkeep_out [C_NUM_QUEUES-1:0];
wire [C_NUM_QUEUES-1:0]				pkt_fifo_tlast_out;

// output from parser
wire [C_S_AXIS_DATA_WIDTH-1:0]		parser_m_axis_tdata [C_NUM_QUEUES-1:0];
wire [C_S_AXIS_TUSER_WIDTH-1:0]		parser_m_axis_tuser [C_NUM_QUEUES-1:0];
wire [C_S_AXIS_DATA_WIDTH/8-1:0]	parser_m_axis_tkeep [C_NUM_QUEUES-1:0];
wire [C_NUM_QUEUES-1:0]				parser_m_axis_tlast;
wire [C_NUM_QUEUES-1:0]				parser_m_axis_tvalid;

wire [C_NUM_QUEUES-1:0]				pkt_fifo_rd_en;
wire [C_NUM_QUEUES-1:0]				pkt_fifo_nearly_full;
wire [C_NUM_QUEUES-1:0]				pkt_fifo_empty;

/*
generate 
	genvar i;
	for (i=0; i<C_NUM_QUEUES; i=i+1) begin:
		sub_pkt_fifo
		fifo_generator_705b 
		pkt_fifo (
			.clk			(clk),                  // input wire clk
  			.srst			(~aresetn),                // input wire srst
  			.din			({parser_m_axis_tdata[i],
								parser_m_axis_tuser[i],
								parser_m_axis_tkeep[i],
								parser_m_axis_tlast[i]}),                  // input wire [704 : 0] din
  			.wr_en			(parser_m_axis_tvalid[i]),              // input wire wr_en
  			.rd_en			(pkt_fifo_rd_en[i]),              // input wire rd_en
  			.dout			({pkt_fifo_tdata_out[i],
								pkt_fifo_tuser_out[i],
								pkt_fifo_tkeep_out[i],
								pkt_fifo_tlast_out[i]}),                // output wire [704 : 0] dout
  			.full			(pkt_fifo_nearly_full[i]),                // output wire full
  			.empty			(pkt_fifo_empty[i]),              // output wire empty
  			.wr_rst_busy	(),  // output wire wr_rst_busy
  			.rd_rst_busy	()  // output wire rd_rst_busy
		);
	end
endgenerate
*/
generate 
	genvar i;
	for (i=0; i<C_NUM_QUEUES; i=i+1) begin:
		sub_pkt_fifo
		fallthrough_small_fifo #(
			.WIDTH(C_S_AXIS_DATA_WIDTH+C_S_AXIS_TUSER_WIDTH+C_S_AXIS_DATA_WIDTH/8+1),
			.MAX_DEPTH_BITS(4)
		)
		pkt_fifo (
			.clk			(clk),                  // input wire clk
  			.reset			(~aresetn),                // input wire srst
  			.din			({parser_m_axis_tdata[i],
								parser_m_axis_tuser[i],
								parser_m_axis_tkeep[i],
								parser_m_axis_tlast[i]}),                  // input wire [704 : 0] din
  			.wr_en			(parser_m_axis_tvalid[i]),              // input wire wr_en
  			.rd_en			(pkt_fifo_rd_en[i]),              // input wire rd_en
  			.dout			({pkt_fifo_tdata_out[i],
								pkt_fifo_tuser_out[i],
								pkt_fifo_tkeep_out[i],
								pkt_fifo_tlast_out[i]}),                // output wire [704 : 0] dout
			.full			(),
  			.nearly_full	(pkt_fifo_nearly_full[i]),                // output wire full
  			.empty			(pkt_fifo_empty[i])              // output wire empty
		);
	end
endgenerate

wire [PKT_VEC_WIDTH-1:0]		last_stg_phv_out [C_NUM_QUEUES-1:0];
wire [PKT_VEC_WIDTH-1:0]		phv_fifo_out [C_NUM_QUEUES-1:0];
wire							last_stg_phv_out_valid [C_NUM_QUEUES-1:0];


wire							phv_fifo_rd_en [C_NUM_QUEUES-1:0];
wire							phv_fifo_nearly_full [C_NUM_QUEUES-1:0];
wire							phv_fifo_empty [C_NUM_QUEUES-1:0];
wire [511:0] high_phv_out [C_NUM_QUEUES-1:0];
wire [511:0] low_phv_out [C_NUM_QUEUES-1:0];

assign phv_fifo_out[0] = {high_phv_out[0], low_phv_out[0]};
assign phv_fifo_out[1] = {high_phv_out[1], low_phv_out[1]};
assign phv_fifo_out[2] = {high_phv_out[2], low_phv_out[2]};
assign phv_fifo_out[3] = {high_phv_out[3], low_phv_out[3]};

assign s_axis_tready_f = (!pkt_fifo_nearly_full[0] ||
							!pkt_fifo_nearly_full[1] ||
							!pkt_fifo_nearly_full[2] ||
							!pkt_fifo_nearly_full[3]) &&
							(!phv_fifo_nearly_full[0] ||
							!phv_fifo_nearly_full[1] ||
							!phv_fifo_nearly_full[2] ||
							!phv_fifo_nearly_full[3]);


generate 
	for (i=0; i<C_NUM_QUEUES; i=i+1) begin:
		sub_phv_fifo_1
		fallthrough_small_fifo #(
			.WIDTH(512),
			.MAX_DEPTH_BITS(6)
		)
		phv_fifo_1 (
			.clk			(clk),
			.reset			(~aresetn),
			.din			(last_stg_phv_out[i][511:0]),
			.wr_en			(last_stg_phv_out_valid[i]),
			.rd_en			(phv_fifo_rd_en[i]),
			.dout			(low_phv_out[i]),
			.full			(),
			.nearly_full	(phv_fifo_nearly_full[i]),
			.empty			(phv_fifo_empty[i])
		);
		/*
		fifo_generator_512b 
		phv_fifo_1 (
		  .clk				(clk),                  // input wire clk
		  .srst				(~aresetn),                // input wire srst
		  .din				(last_stg_phv_out[i][511:0]),                  // input wire [511 : 0] din
		  .wr_en			(last_stg_phv_out_valid[i]),              // input wire wr_en
		  .rd_en			(phv_fifo_rd_en[i]),              // input wire rd_en
		  .dout				(low_phv_out[i]),                // output wire [511 : 0] dout
		  .full				(phv_fifo_nearly_full[i]),                // output wire full
		  .empty			(phv_fifo_empty[i]),              // output wire empty
		  .wr_rst_busy		(),  // output wire wr_rst_busy
		  .rd_rst_busy		()  // output wire rd_rst_busy
		);*/
	end
endgenerate

generate
	for (i=0; i<C_NUM_QUEUES; i=i+1) begin:
		sub_phv_fifo_2
		fallthrough_small_fifo #(
			.WIDTH(512),
			.MAX_DEPTH_BITS(6)
		)
		phv_fifo_2 (
			.clk			(clk),
			.reset			(~aresetn),
			.din			(last_stg_phv_out[i][1023:512]),
			.wr_en			(last_stg_phv_out_valid[i]),
			.rd_en			(phv_fifo_rd_en[i]),
			.dout			(high_phv_out[i]),
			.full			(),
			.nearly_full	(),
			.empty			()
		);
		/*
		fifo_generator_512b 
		phv_fifo_2 (
		  .clk				(clk),                  // input wire clk
		  .srst				(~aresetn),                // input wire srst
		  .din				(last_stg_phv_out[i][1023:512]),                  // input wire [521 : 0] din
		  .wr_en			(last_stg_phv_out_valid[i]),              // input wire wr_en
		  .rd_en			(phv_fifo_rd_en[i]),              // input wire rd_en
		  .dout				(high_phv_out[i]),                // output wire [521 : 0] dout
		  .full				(),                // output wire full
		  .empty			(),              // output wire empty
		  .wr_rst_busy		(),  // output wire wr_rst_busy
		  .rd_rst_busy		()  // output wire rd_rst_busy
		);*/
	end
endgenerate

wire [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_2;
wire [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_2;
wire [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_2;
wire 										ctrl_s_axis_tvalid_2;
wire 										ctrl_s_axis_tlast_2;

reg [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_2_r;
reg [((C_S_AXIS_DATA_WIDTH/8))-1:0]			ctrl_s_axis_tkeep_2_r;
reg [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_2_r;
reg 										ctrl_s_axis_tvalid_2_r;
reg 										ctrl_s_axis_tlast_2_r;

wire [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_3;
wire [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_3;
wire [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_3;
wire 										ctrl_s_axis_tvalid_3;
wire 										ctrl_s_axis_tlast_3;

reg [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_3_r;
reg [((C_S_AXIS_DATA_WIDTH/8))-1:0]			ctrl_s_axis_tkeep_3_r;
reg [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_3_r;
reg 										ctrl_s_axis_tvalid_3_r;
reg 										ctrl_s_axis_tlast_3_r;

wire [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_4;
wire [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_4;
wire [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_4;
wire 										ctrl_s_axis_tvalid_4;
wire 										ctrl_s_axis_tlast_4;

reg [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_4_r;
reg [((C_S_AXIS_DATA_WIDTH/8))-1:0]			ctrl_s_axis_tkeep_4_r;
reg [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_4_r;
reg 										ctrl_s_axis_tvalid_4_r;
reg 										ctrl_s_axis_tlast_4_r;

wire [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_5;
wire [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_5;
wire [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_5;
wire 										ctrl_s_axis_tvalid_5;
wire 										ctrl_s_axis_tlast_5;

reg [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_5_r;
reg [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_5_r;
reg [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_5_r;
reg 										ctrl_s_axis_tvalid_5_r;
reg 										ctrl_s_axis_tlast_5_r;

wire [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_6;
wire [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_6;
wire [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_6;
wire 										ctrl_s_axis_tvalid_6;
wire 										ctrl_s_axis_tlast_6;

reg [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_6_r;
reg [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_6_r;
reg [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_6_r;
reg 										ctrl_s_axis_tvalid_6_r;
reg 										ctrl_s_axis_tlast_6_r;

wire [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_7;
wire [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_7;
wire [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_7;
wire 										ctrl_s_axis_tvalid_7;
wire 										ctrl_s_axis_tlast_7;

reg [C_S_AXIS_DATA_WIDTH-1:0]				ctrl_s_axis_tdata_7_r;
reg [((C_S_AXIS_DATA_WIDTH/8))-1:0]		ctrl_s_axis_tkeep_7_r;
reg [C_S_AXIS_TUSER_WIDTH-1:0]				ctrl_s_axis_tuser_7_r;
reg 										ctrl_s_axis_tvalid_7_r;
reg 										ctrl_s_axis_tlast_7_r;

parser_top #(
    .C_S_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH), //for 100g mac exclusively
	.C_S_AXIS_TUSER_WIDTH(),
	.PKT_HDR_LEN()
)
phv_parser
(
	.axis_clk		(clk),
	.aresetn		(aresetn),
	// input slvae axi stream
	.s_axis_tdata	(s_axis_tdata_f_reg),
	.s_axis_tuser	(s_axis_tuser_f_reg),
	.s_axis_tkeep	(s_axis_tkeep_f_reg),
	// .s_axis_tvalid	(s_axis_tvalid_f_reg & s_axis_tready_f),
	.s_axis_tvalid	(s_axis_tvalid_f_reg),
	.s_axis_tlast	(s_axis_tlast_f_reg),
	.s_axis_tready	(s_axis_tready_p),

	.s_vlan_id			(s_vlan_id_r),
	.s_vlan_id_valid	(s_vlan_id_valid_r),

	// output
	.parser_valid		(stg0_phv_in_valid),
	.pkt_hdr_vec		(stg0_phv_in),
	.out_vlan			(stg0_vlan_in),
	.out_vlan_valid		(stg0_vlan_valid_in),
	.out_vlan_ready		(stg0_vlan_ready),
	// 
	.stg_ready_in		(stg0_ready),

	// output to different pkt fifos
	.m_axis_tdata_0					(parser_m_axis_tdata[0]),
	.m_axis_tuser_0					(parser_m_axis_tuser[0]),
	.m_axis_tkeep_0					(parser_m_axis_tkeep[0]),
	.m_axis_tlast_0					(parser_m_axis_tlast[0]),
	.m_axis_tvalid_0				(parser_m_axis_tvalid[0]),
	.m_axis_tready_0				(~pkt_fifo_nearly_full[0]),

	.m_axis_tdata_1					(parser_m_axis_tdata[1]),
	.m_axis_tuser_1					(parser_m_axis_tuser[1]),
	.m_axis_tkeep_1					(parser_m_axis_tkeep[1]),
	.m_axis_tlast_1					(parser_m_axis_tlast[1]),
	.m_axis_tvalid_1				(parser_m_axis_tvalid[1]),
	.m_axis_tready_1				(~pkt_fifo_nearly_full[1]),

	.m_axis_tdata_2					(parser_m_axis_tdata[2]),
	.m_axis_tuser_2					(parser_m_axis_tuser[2]),
	.m_axis_tkeep_2					(parser_m_axis_tkeep[2]),
	.m_axis_tlast_2					(parser_m_axis_tlast[2]),
	.m_axis_tvalid_2				(parser_m_axis_tvalid[2]),
	.m_axis_tready_2				(~pkt_fifo_nearly_full[2]),

	.m_axis_tdata_3					(parser_m_axis_tdata[3]),
	.m_axis_tuser_3					(parser_m_axis_tuser[3]),
	.m_axis_tkeep_3					(parser_m_axis_tkeep[3]),
	.m_axis_tlast_3					(parser_m_axis_tlast[3]),
	.m_axis_tvalid_3				(parser_m_axis_tvalid[3]),
	.m_axis_tready_3				(~pkt_fifo_nearly_full[3]),

	// control path
    .ctrl_s_axis_tdata(ctrl_s_axis_tdata_1_r),
	.ctrl_s_axis_tuser(ctrl_s_axis_tuser_1_r),
	.ctrl_s_axis_tkeep(ctrl_s_axis_tkeep_1_r),
	.ctrl_s_axis_tlast(ctrl_s_axis_tlast_1_r),
	.ctrl_s_axis_tvalid(ctrl_s_axis_tvalid_1_r),

    .ctrl_m_axis_tdata(ctrl_s_axis_tdata_2),
	.ctrl_m_axis_tuser(ctrl_s_axis_tuser_2),
	.ctrl_m_axis_tkeep(ctrl_s_axis_tkeep_2),
	.ctrl_m_axis_tlast(ctrl_s_axis_tlast_2),
	.ctrl_m_axis_tvalid(ctrl_s_axis_tvalid_2)
);

stage #(
	.C_S_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
	.STAGE_ID(0)
)
stage0
(
	.axis_clk				(clk),
    .aresetn				(aresetn),

	// input
    .phv_in					(stg0_phv_in_d1),
    .phv_in_valid			(stg0_phv_in_valid_d1),
	.vlan_in				(stg0_vlan_in_r),
	.vlan_valid_in			(stg0_vlan_valid_in_r),
	.vlan_ready_out			(stg0_vlan_ready),
	// output
	.vlan_out				(stg0_vlan_out),
	.vlan_valid_out			(stg0_vlan_valid_out),
	.vlan_out_ready			(stg1_vlan_ready),
	// output
    .phv_out				(stg0_phv_out),
    .phv_out_valid			(stg0_phv_out_valid),
	// back-pressure signals
	.stage_ready_out		(stg0_ready),
	.stage_ready_in			(stg1_ready),

	// control path
    .c_s_axis_tdata(ctrl_s_axis_tdata_2_r),
	.c_s_axis_tuser(ctrl_s_axis_tuser_2_r),
	.c_s_axis_tkeep(ctrl_s_axis_tkeep_2_r),
	.c_s_axis_tlast(ctrl_s_axis_tlast_2_r),
	.c_s_axis_tvalid(ctrl_s_axis_tvalid_2_r),

    .c_m_axis_tdata(ctrl_s_axis_tdata_3),
	.c_m_axis_tuser(ctrl_s_axis_tuser_3),
	.c_m_axis_tkeep(ctrl_s_axis_tkeep_3),
	.c_m_axis_tlast(ctrl_s_axis_tlast_3),
	.c_m_axis_tvalid(ctrl_s_axis_tvalid_3)
);

stage #(
	.C_S_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
	.STAGE_ID(1)
)
stage1
(
	.axis_clk				(clk),
    .aresetn				(aresetn),

	// input
    .phv_in					(stg0_phv_out_d1),
    .phv_in_valid			(stg0_phv_out_valid_d1),
	.vlan_in				(stg0_vlan_out_r),
	.vlan_valid_in			(stg0_vlan_valid_out_r),
	.vlan_ready_out			(stg1_vlan_ready),
	// output
	.vlan_out				(stg1_vlan_out),
	.vlan_valid_out			(stg1_vlan_valid_out),
	.vlan_out_ready			(stg2_vlan_ready),
	// output
    .phv_out				(stg1_phv_out),
    .phv_out_valid			(stg1_phv_out_valid),
	// back-pressure signals
	.stage_ready_out		(stg1_ready),
	.stage_ready_in			(stg2_ready),

	// control path
    .c_s_axis_tdata(ctrl_s_axis_tdata_3_r),
	.c_s_axis_tuser(ctrl_s_axis_tuser_3_r),
	.c_s_axis_tkeep(ctrl_s_axis_tkeep_3_r),
	.c_s_axis_tlast(ctrl_s_axis_tlast_3_r),
	.c_s_axis_tvalid(ctrl_s_axis_tvalid_3_r),

    .c_m_axis_tdata(ctrl_s_axis_tdata_4),
	.c_m_axis_tuser(ctrl_s_axis_tuser_4),
	.c_m_axis_tkeep(ctrl_s_axis_tkeep_4),
	.c_m_axis_tlast(ctrl_s_axis_tlast_4),
	.c_m_axis_tvalid(ctrl_s_axis_tvalid_4)
);

stage #(
	.C_S_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
	.STAGE_ID(2)
)
stage2
(
	.axis_clk				(clk),
    .aresetn				(aresetn),

	// input
    .phv_in					(stg1_phv_out_d1),
    .phv_in_valid			(stg1_phv_out_valid_d1),
	.vlan_in				(stg1_vlan_out_r),
	.vlan_valid_in			(stg1_vlan_valid_out_r),
	.vlan_ready_out			(stg2_vlan_ready),
	// output
	.vlan_out				(stg2_vlan_out),
	.vlan_valid_out			(stg2_vlan_valid_out),
	.vlan_out_ready			(stg3_vlan_ready),
	// output
    .phv_out				(stg2_phv_out),
    .phv_out_valid			(stg2_phv_out_valid),
	// back-pressure signals
	.stage_ready_out		(stg2_ready),
	.stage_ready_in			(stg3_ready),

	// control path
    .c_s_axis_tdata(ctrl_s_axis_tdata_4_r),
	.c_s_axis_tuser(ctrl_s_axis_tuser_4_r),
	.c_s_axis_tkeep(ctrl_s_axis_tkeep_4_r),
	.c_s_axis_tlast(ctrl_s_axis_tlast_4_r),
	.c_s_axis_tvalid(ctrl_s_axis_tvalid_4_r),

    .c_m_axis_tdata(ctrl_s_axis_tdata_5),
	.c_m_axis_tuser(ctrl_s_axis_tuser_5),
	.c_m_axis_tkeep(ctrl_s_axis_tkeep_5),
	.c_m_axis_tlast(ctrl_s_axis_tlast_5),
	.c_m_axis_tvalid(ctrl_s_axis_tvalid_5)
);

stage #(
	.C_S_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
	.STAGE_ID(3)
)
stage3
(
	.axis_clk				(clk),
    .aresetn				(aresetn),

	// input
    .phv_in					(stg2_phv_out_d1),
    .phv_in_valid			(stg2_phv_out_valid_d1),
	.vlan_in				(stg2_vlan_out_r),
	.vlan_valid_in			(stg2_vlan_valid_out_r),
	.vlan_ready_out			(stg3_vlan_ready),
	// output
	.vlan_out				(stg3_vlan_out),
	.vlan_valid_out			(stg3_vlan_valid_out),
	.vlan_out_ready			(last_stg_vlan_ready),
	// output
    .phv_out				(stg3_phv_out),
    .phv_out_valid			(stg3_phv_out_valid),
	// back-pressure signals
	.stage_ready_out		(stg3_ready),
	.stage_ready_in			(last_stg_ready),

	// control path
    .c_s_axis_tdata(ctrl_s_axis_tdata_5_r),
	.c_s_axis_tuser(ctrl_s_axis_tuser_5_r),
	.c_s_axis_tkeep(ctrl_s_axis_tkeep_5_r),
	.c_s_axis_tlast(ctrl_s_axis_tlast_5_r),
	.c_s_axis_tvalid(ctrl_s_axis_tvalid_5_r),

    .c_m_axis_tdata(ctrl_s_axis_tdata_6),
	.c_m_axis_tuser(ctrl_s_axis_tuser_6),
	.c_m_axis_tkeep(ctrl_s_axis_tkeep_6),
	.c_m_axis_tlast(ctrl_s_axis_tlast_6),
	.c_m_axis_tvalid(ctrl_s_axis_tvalid_6)
);

// [NOTICE] change to last stage
last_stage #(
	.C_S_AXIS_DATA_WIDTH(512),
	.STAGE_ID(4)
)
stage4
(
	.axis_clk				(clk),
    .aresetn				(aresetn),

	// input
    .phv_in					(stg3_phv_out_d1),
    .phv_in_valid			(stg3_phv_out_valid_d1),
	.vlan_in				(stg3_vlan_out_r),
	.vlan_valid_in			(stg3_vlan_valid_out_r),
	.vlan_ready_out			(last_stg_vlan_ready),
	// back-pressure signals
	.stage_ready_out		(last_stg_ready),
    // .phv_in					(stg0_phv_in_d1),
    // .phv_in_valid			(stg0_phv_in_valid_d1),
	// .vlan_in				(stg0_vlan_in_r),
	// .vlan_valid_in			(stg0_vlan_valid_in_r),
	// .vlan_ready_out			(stg0_vlan_ready),
	// // back-pressure signals
	// .stage_ready_out		(stg0_ready),
	// output
    .phv_out_0				(last_stg_phv_out[0]),
    .phv_out_valid_0		(last_stg_phv_out_valid[0]),
	.phv_fifo_ready_0		(~phv_fifo_nearly_full[0]),

    .phv_out_1				(last_stg_phv_out[1]),
    .phv_out_valid_1		(last_stg_phv_out_valid[1]),
	.phv_fifo_ready_1		(~phv_fifo_nearly_full[1]),

    .phv_out_2				(last_stg_phv_out[2]),
    .phv_out_valid_2		(last_stg_phv_out_valid[2]),
	.phv_fifo_ready_2		(~phv_fifo_nearly_full[2]),

    .phv_out_3				(last_stg_phv_out[3]),
    .phv_out_valid_3		(last_stg_phv_out_valid[3]),
	.phv_fifo_ready_3		(~phv_fifo_nearly_full[3]),

	// control path
    .c_s_axis_tdata(ctrl_s_axis_tdata_6_r),
	.c_s_axis_tuser(ctrl_s_axis_tuser_6_r),
	.c_s_axis_tkeep(ctrl_s_axis_tkeep_6_r),
	.c_s_axis_tlast(ctrl_s_axis_tlast_6_r),
	.c_s_axis_tvalid(ctrl_s_axis_tvalid_6_r),

    .c_m_axis_tdata(ctrl_s_axis_tdata_7),
	.c_m_axis_tuser(ctrl_s_axis_tuser_7),
	.c_m_axis_tkeep(ctrl_s_axis_tkeep_7),
	.c_m_axis_tlast(ctrl_s_axis_tlast_7),
	.c_m_axis_tvalid(ctrl_s_axis_tvalid_7)
);

wire [C_S_AXIS_DATA_WIDTH-1:0]			depar_out_tdata [C_NUM_QUEUES-1:0];
wire [((C_S_AXIS_DATA_WIDTH/8))-1:0]	depar_out_tkeep [C_NUM_QUEUES-1:0];
wire [C_S_AXIS_TUSER_WIDTH-1:0]			depar_out_tuser [C_NUM_QUEUES-1:0];
wire									depar_out_tvalid [C_NUM_QUEUES-1:0];
wire 									depar_out_tlast [C_NUM_QUEUES-1:0];
wire 									depar_out_tready [C_NUM_QUEUES-1:0];

reg  [C_S_AXIS_DATA_WIDTH-1:0]			depar_out_tdata_d1 [C_NUM_QUEUES-1:0];
reg  [((C_S_AXIS_DATA_WIDTH/8))-1:0]	depar_out_tkeep_d1 [C_NUM_QUEUES-1:0];
reg  [C_S_AXIS_TUSER_WIDTH-1:0]			depar_out_tuser_d1 [C_NUM_QUEUES-1:0];
reg 									depar_out_tvalid_d1 [C_NUM_QUEUES-1:0];
reg  									depar_out_tlast_d1 [C_NUM_QUEUES-1:0];
// multiple deparser + output arbiter
generate
	for (i=0; i<C_NUM_QUEUES; i=i+1) begin:
		sub_deparser_top
		deparser_top #(
			.C_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
			.C_AXIS_TUSER_WIDTH(C_S_AXIS_TUSER_WIDTH),
			.C_PKT_VEC_WIDTH(),
		    .DEPARSER_MOD_ID()
		)
		phv_deparser (
			.axis_clk				(clk),
			.aresetn				(aresetn),
		
			//data plane
			.pkt_fifo_tdata			(pkt_fifo_tdata_out[i]),
			.pkt_fifo_tkeep			(pkt_fifo_tkeep_out[i]),
			.pkt_fifo_tuser			(pkt_fifo_tuser_out[i]),
			.pkt_fifo_tlast			(pkt_fifo_tlast_out[i]),
			.pkt_fifo_empty			(pkt_fifo_empty[i]),
			// output from STAGE
			.pkt_fifo_rd_en			(pkt_fifo_rd_en[i]),
		
			.phv_fifo_out			(phv_fifo_out[i]),
			.phv_fifo_empty			(phv_fifo_empty[i]),
			.phv_fifo_rd_en			(phv_fifo_rd_en[i]),
			// output
			.depar_out_tdata		(depar_out_tdata[i]),
			.depar_out_tkeep		(depar_out_tkeep[i]),
			.depar_out_tuser		(depar_out_tuser[i]),
			.depar_out_tvalid		(depar_out_tvalid[i]),
			.depar_out_tlast		(depar_out_tlast[i]),
			// input
			.depar_out_tready		(depar_out_tready[i]),
		
			//control path
			.ctrl_s_axis_tdata(ctrl_s_axis_tdata_7_r),
			.ctrl_s_axis_tuser(ctrl_s_axis_tuser_7_r),
			.ctrl_s_axis_tkeep(ctrl_s_axis_tkeep_7_r),
			.ctrl_s_axis_tvalid(ctrl_s_axis_tvalid_7_r),
			.ctrl_s_axis_tlast(ctrl_s_axis_tlast_7_r)
		);
	end
endgenerate

// output arbiter
output_arbiter #(
	.C_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
	.C_AXIS_TUSER_WIDTH(C_S_AXIS_TUSER_WIDTH)
)
out_arb (
	.axis_clk						(clk),
	.aresetn						(aresetn),
	// output
	.m_axis_tdata					(m_axis_tdata),
	.m_axis_tkeep					(m_axis_tkeep),
	.m_axis_tuser					(m_axis_tuser),
	.m_axis_tlast					(m_axis_tlast),
	.m_axis_tvalid					(m_axis_tvalid),
	.m_axis_tready					(m_axis_tready),
	// input from deparser
	.s_axis_tdata_0					(depar_out_tdata_d1[0]),
	.s_axis_tkeep_0					(depar_out_tkeep_d1[0]),
	.s_axis_tuser_0					(depar_out_tuser_d1[0]),
	.s_axis_tlast_0					(depar_out_tlast_d1[0]),
	.s_axis_tvalid_0				(depar_out_tvalid_d1[0]),
	.s_axis_tready_0				(depar_out_tready[0]),

	.s_axis_tdata_1					(depar_out_tdata_d1[1]),
	.s_axis_tkeep_1					(depar_out_tkeep_d1[1]),
	.s_axis_tuser_1					(depar_out_tuser_d1[1]),
	.s_axis_tlast_1					(depar_out_tlast_d1[1]),
	.s_axis_tvalid_1				(depar_out_tvalid_d1[1]),
	.s_axis_tready_1				(depar_out_tready[1]),

	.s_axis_tdata_2					(depar_out_tdata_d1[2]),
	.s_axis_tkeep_2					(depar_out_tkeep_d1[2]),
	.s_axis_tuser_2					(depar_out_tuser_d1[2]),
	.s_axis_tlast_2					(depar_out_tlast_d1[2]),
	.s_axis_tvalid_2				(depar_out_tvalid_d1[2]),
	.s_axis_tready_2				(depar_out_tready[2]),

	.s_axis_tdata_3					(depar_out_tdata_d1[3]),
	.s_axis_tkeep_3					(depar_out_tkeep_d1[3]),
	.s_axis_tuser_3					(depar_out_tuser_d1[3]),
	.s_axis_tlast_3					(depar_out_tlast_d1[3]),
	.s_axis_tvalid_3				(depar_out_tvalid_d1[3]),
	.s_axis_tready_3				(depar_out_tready[3])
);


always @(posedge clk) begin
	if (~aresetn) begin
		stg0_phv_in_valid_d1 <= 0;
		stg0_phv_out_valid_d1 <= 0;
		stg1_phv_out_valid_d1 <= 0;
		stg2_phv_out_valid_d1 <= 0;
		stg3_phv_out_valid_d1 <= 0;

		stg0_phv_in_d1 <= 0;
		stg0_phv_out_d1 <= 0;
		stg1_phv_out_d1 <= 0;
		stg2_phv_out_d1 <= 0;
		stg3_phv_out_d1 <= 0;
		//
		s_axis_tdata_f_reg <= 0;
		s_axis_tkeep_f_reg <= 0;
		s_axis_tuser_f_reg <= 0;
		s_axis_tlast_f_reg <= 0;
		s_axis_tvalid_f_reg <= 0;
		//
		s_vlan_id_r <= 0;
		s_vlan_id_valid_r <= 0;
		//
		stg0_vlan_in_r <= 0;
		stg0_vlan_valid_in_r <= 0;
		stg0_vlan_out_r <= 0;
		stg0_vlan_valid_out_r <= 0;
		stg1_vlan_out_r <= 0;
		stg1_vlan_valid_out_r <= 0;
		stg2_vlan_out_r <= 0;
		stg2_vlan_valid_out_r <= 0;
		stg3_vlan_out_r <= 0;
		stg3_vlan_valid_out_r <= 0;
	end
	else begin
		stg0_phv_in_valid_d1 <= stg0_phv_in_valid;
		stg0_phv_out_valid_d1 <= stg0_phv_out_valid;
		stg1_phv_out_valid_d1 <= stg1_phv_out_valid;
		stg2_phv_out_valid_d1 <= stg2_phv_out_valid;
		stg3_phv_out_valid_d1 <= stg3_phv_out_valid;

		stg0_phv_in_d1 <= stg0_phv_in;
		stg0_phv_out_d1 <= stg0_phv_out;
		stg1_phv_out_d1 <= stg1_phv_out;
		stg2_phv_out_d1 <= stg2_phv_out;
		stg3_phv_out_d1 <= stg3_phv_out;
		//
		s_axis_tdata_f_reg <= s_axis_tdata_f;
		s_axis_tkeep_f_reg <= s_axis_tkeep_f;
		s_axis_tuser_f_reg <= s_axis_tuser_f;
		s_axis_tlast_f_reg <= s_axis_tlast_f;
		s_axis_tvalid_f_reg <= s_axis_tvalid_f;
		//
		s_vlan_id_r <= s_vlan_id;
		s_vlan_id_valid_r <= s_vlan_id_valid;
		//
		stg0_vlan_in_r <= stg0_vlan_in;
		stg0_vlan_valid_in_r <= stg0_vlan_valid_in;
		stg0_vlan_out_r <= stg0_vlan_out;
		stg0_vlan_valid_out_r <= stg0_vlan_valid_out;
		stg1_vlan_out_r <= stg1_vlan_out;
		stg1_vlan_valid_out_r <= stg1_vlan_valid_out;
		stg2_vlan_out_r <= stg2_vlan_out;
		stg2_vlan_valid_out_r <= stg2_vlan_valid_out;
		stg3_vlan_out_r <= stg3_vlan_out;
		stg3_vlan_valid_out_r <= stg3_vlan_valid_out;
	end
end

// delay deparser out
always @(posedge clk) begin
	if (~aresetn) begin
		for (idx=0; idx<C_NUM_QUEUES; idx=idx+1) begin
			depar_out_tdata_d1[idx] <= 0;
			depar_out_tkeep_d1[idx] <= 0;
			depar_out_tuser_d1[idx] <= 0;
			depar_out_tvalid_d1[idx] <= 0;
			depar_out_tlast_d1[idx] <= 0;
		end
	end
	else begin
		for (idx=0; idx<C_NUM_QUEUES; idx=idx+1) begin
			depar_out_tdata_d1[idx] <= depar_out_tdata[idx];
			depar_out_tkeep_d1[idx] <= depar_out_tkeep[idx];
			depar_out_tuser_d1[idx] <= depar_out_tuser[idx];
			depar_out_tvalid_d1[idx] <= depar_out_tvalid[idx];
			depar_out_tlast_d1[idx] <= depar_out_tlast[idx];
		end
	end
end

always @(posedge clk) begin
	if (~aresetn) begin
		ctrl_s_axis_tdata_1_r <= 0;
		ctrl_s_axis_tuser_1_r <= 0;
		ctrl_s_axis_tkeep_1_r <= 0;
		ctrl_s_axis_tlast_1_r <= 0;
		ctrl_s_axis_tvalid_1_r <= 0;

		ctrl_s_axis_tdata_2_r <= 0;
		ctrl_s_axis_tuser_2_r <= 0;
		ctrl_s_axis_tkeep_2_r <= 0;
		ctrl_s_axis_tlast_2_r <= 0;
		ctrl_s_axis_tvalid_2_r <= 0;

		ctrl_s_axis_tdata_3_r <= 0;
		ctrl_s_axis_tuser_3_r <= 0;
		ctrl_s_axis_tkeep_3_r <= 0;
		ctrl_s_axis_tlast_3_r <= 0;
		ctrl_s_axis_tvalid_3_r <= 0;

		ctrl_s_axis_tdata_4_r <= 0;
		ctrl_s_axis_tuser_4_r <= 0;
		ctrl_s_axis_tkeep_4_r <= 0;
		ctrl_s_axis_tlast_4_r <= 0;
		ctrl_s_axis_tvalid_4_r <= 0;

		ctrl_s_axis_tdata_5_r <= 0;
		ctrl_s_axis_tuser_5_r <= 0;
		ctrl_s_axis_tkeep_5_r <= 0;
		ctrl_s_axis_tlast_5_r <= 0;
		ctrl_s_axis_tvalid_5_r <= 0;

		ctrl_s_axis_tdata_6_r <= 0;
		ctrl_s_axis_tuser_6_r <= 0;
		ctrl_s_axis_tkeep_6_r <= 0;
		ctrl_s_axis_tlast_6_r <= 0;
		ctrl_s_axis_tvalid_6_r <= 0;

		ctrl_s_axis_tdata_7_r <= 0;
		ctrl_s_axis_tuser_7_r <= 0;
		ctrl_s_axis_tkeep_7_r <= 0;
		ctrl_s_axis_tlast_7_r <= 0;
		ctrl_s_axis_tvalid_7_r <= 0;
	end
	else begin
		ctrl_s_axis_tdata_1_r <= ctrl_s_axis_tdata_1;
		ctrl_s_axis_tuser_1_r <= ctrl_s_axis_tuser_1;
		ctrl_s_axis_tkeep_1_r <= ctrl_s_axis_tkeep_1;
		ctrl_s_axis_tlast_1_r <= ctrl_s_axis_tlast_1;
		ctrl_s_axis_tvalid_1_r <= ctrl_s_axis_tvalid_1;

		ctrl_s_axis_tdata_2_r <= ctrl_s_axis_tdata_2;
		ctrl_s_axis_tuser_2_r <= ctrl_s_axis_tuser_2;
		ctrl_s_axis_tkeep_2_r <= ctrl_s_axis_tkeep_2;
		ctrl_s_axis_tlast_2_r <= ctrl_s_axis_tlast_2;
		ctrl_s_axis_tvalid_2_r <= ctrl_s_axis_tvalid_2;

		ctrl_s_axis_tdata_3_r <= ctrl_s_axis_tdata_3;
		ctrl_s_axis_tuser_3_r <= ctrl_s_axis_tuser_3;
		ctrl_s_axis_tkeep_3_r <= ctrl_s_axis_tkeep_3;
		ctrl_s_axis_tlast_3_r <= ctrl_s_axis_tlast_3;
		ctrl_s_axis_tvalid_3_r <= ctrl_s_axis_tvalid_3;

		ctrl_s_axis_tdata_4_r <= ctrl_s_axis_tdata_4;
		ctrl_s_axis_tuser_4_r <= ctrl_s_axis_tuser_4;
		ctrl_s_axis_tkeep_4_r <= ctrl_s_axis_tkeep_4;
		ctrl_s_axis_tlast_4_r <= ctrl_s_axis_tlast_4;
		ctrl_s_axis_tvalid_4_r <= ctrl_s_axis_tvalid_4;

		ctrl_s_axis_tdata_5_r <= ctrl_s_axis_tdata_5;
		ctrl_s_axis_tuser_5_r <= ctrl_s_axis_tuser_5;
		ctrl_s_axis_tkeep_5_r <= ctrl_s_axis_tkeep_5;
		ctrl_s_axis_tlast_5_r <= ctrl_s_axis_tlast_5;
		ctrl_s_axis_tvalid_5_r <= ctrl_s_axis_tvalid_5;

		ctrl_s_axis_tdata_6_r <= ctrl_s_axis_tdata_6;
		ctrl_s_axis_tuser_6_r <= ctrl_s_axis_tuser_6;
		ctrl_s_axis_tkeep_6_r <= ctrl_s_axis_tkeep_6;
		ctrl_s_axis_tlast_6_r <= ctrl_s_axis_tlast_6;
		ctrl_s_axis_tvalid_6_r <= ctrl_s_axis_tvalid_6;

		ctrl_s_axis_tdata_7_r <= ctrl_s_axis_tdata_7;
		ctrl_s_axis_tuser_7_r <= ctrl_s_axis_tuser_7;
		ctrl_s_axis_tkeep_7_r <= ctrl_s_axis_tkeep_7;
		ctrl_s_axis_tlast_7_r <= ctrl_s_axis_tlast_7;
		ctrl_s_axis_tvalid_7_r <= ctrl_s_axis_tvalid_7;

	end
end

endmodule
