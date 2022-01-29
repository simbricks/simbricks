`timescale 1ns / 1ps

module lookup_engine_top #(
    parameter C_S_AXIS_DATA_WIDTH = 512,
    parameter C_S_AXIS_TUSER_WIDTH = 128,
    parameter STAGE_ID = 0,
    parameter PHV_LEN = 48*8+32*8+16*8+256,
    parameter KEY_LEN = 48*2+32*2+16*2+5,
    parameter ACT_LEN = 625,
    parameter LOOKUP_ID = 2,
	parameter C_VLANID_WIDTH = 12
)
(
    input clk,
    input rst_n,

    //output from key extractor
    input [KEY_LEN-1:0]           extract_key,
    input                         key_valid,
	input							phv_valid,
    input [PHV_LEN-1:0]				phv_in,
	output							ready_out,

    //output to the action engine
    output [ACT_LEN-1:0]			action,
    output							action_valid,
    output [PHV_LEN-1:0]			phv_out, 
	input							ready_in,

	// output vlan to ALU vlan fifo
	output [C_VLANID_WIDTH-1:0]		act_vlan_out,
	output							act_vlan_valid_out,
	input							act_vlan_ready,


    //control path
    input [C_S_AXIS_DATA_WIDTH-1:0]			    c_s_axis_tdata,
	input [C_S_AXIS_TUSER_WIDTH-1:0]		    c_s_axis_tuser,
	input [C_S_AXIS_DATA_WIDTH/8-1:0]		    c_s_axis_tkeep,
	input									    c_s_axis_tvalid,
	input									    c_s_axis_tlast,

    output [C_S_AXIS_DATA_WIDTH-1:0]			c_m_axis_tdata,
	output [C_S_AXIS_TUSER_WIDTH-1:0]			c_m_axis_tuser,
	output [C_S_AXIS_DATA_WIDTH/8-1:0]			c_m_axis_tkeep,
	output										c_m_axis_tvalid,
	output							    		c_m_axis_tlast
);

wire [C_S_AXIS_DATA_WIDTH-1:0]		c_s_axis_tdata_0;
wire [C_S_AXIS_TUSER_WIDTH-1:0]		c_s_axis_tuser_0;
wire [C_S_AXIS_DATA_WIDTH/8-1:0]	c_s_axis_tkeep_0;
wire								c_s_axis_tvalid_0;
wire								c_s_axis_tlast_0;

wire [PHV_LEN-1:0]					cam_phv_out;
wire								cam_phv_out_valid;
wire [3:0]							cam_match_addr_out;
wire								cam_if_match;
wire								lke_ram_ready;

reg [PHV_LEN-1:0]				cam_phv_out_d1;
reg								cam_phv_out_valid_d1;
reg [3:0]						cam_match_addr_out_d1;
reg								cam_if_match_d1;

always @(posedge clk) begin
	if (~rst_n) begin
		cam_phv_out_d1 <= 0;
		cam_phv_out_valid_d1 <= 0;
		cam_match_addr_out_d1 <= 0;
		cam_if_match_d1 <= 0;
	end
	else begin
		cam_phv_out_d1 <= cam_phv_out;
		cam_phv_out_valid_d1 <= cam_phv_out_valid;
		cam_match_addr_out_d1 <= cam_match_addr_out;
		cam_if_match_d1 <= cam_if_match;
	end
end


lke_cam_part #(
    .C_S_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
    .C_S_AXIS_TUSER_WIDTH(C_S_AXIS_TUSER_WIDTH),
    .STAGE_ID(STAGE_ID),
    .PHV_LEN(PHV_LEN),
    .KEY_LEN(KEY_LEN),
    .ACT_LEN(ACT_LEN),
    .LOOKUP_ID(LOOKUP_ID),
	.C_VLANID_WIDTH(C_VLANID_WIDTH)
)
lke_cam (
	.clk		(clk),
	.rst_n		(rst_n),

	.extract_key	(extract_key),
	.key_valid		(key_valid),
	.phv_valid		(phv_valid),
	.phv_in			(phv_in),
	.ready_out		(ready_out),
	//
	.phv_out		(cam_phv_out),
	.phv_out_valid	(cam_phv_out_valid),
	.match_addr_out	(cam_match_addr_out),
	.if_match		(cam_if_match),
	.ready_in		(lke_ram_ready),
	//
	.c_s_axis_tdata		(c_s_axis_tdata),
	.c_s_axis_tuser		(c_s_axis_tuser),
	.c_s_axis_tkeep		(c_s_axis_tkeep),
	.c_s_axis_tvalid	(c_s_axis_tvalid),
	.c_s_axis_tlast		(c_s_axis_tlast),

	.c_m_axis_tdata		(c_s_axis_tdata_0),
	.c_m_axis_tuser		(c_s_axis_tuser_0),
	.c_m_axis_tkeep		(c_s_axis_tkeep_0),
	.c_m_axis_tvalid	(c_s_axis_tvalid_0),
	.c_m_axis_tlast		(c_s_axis_tlast_0)
);

lke_ram_part #(
    .C_S_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
    .C_S_AXIS_TUSER_WIDTH(C_S_AXIS_TUSER_WIDTH),
    .STAGE_ID(STAGE_ID),
    .PHV_LEN(PHV_LEN),
    .KEY_LEN(KEY_LEN),
    .ACT_LEN(ACT_LEN),
    .LOOKUP_ID(LOOKUP_ID),
	.C_VLANID_WIDTH(C_VLANID_WIDTH)
)
lke_ram (
	.clk			(clk),
	.rst_n			(rst_n),

	.phv_in			(cam_phv_out_d1),
	.phv_valid		(cam_phv_out_valid_d1),
	.match_addr		(cam_match_addr_out_d1),
	.if_match		(cam_if_match_d1),
	.ready_out		(lke_ram_ready),

	//
	.action			(action),
	.action_valid	(action_valid),
	.phv_out		(phv_out),
	.ready_in		(ready_in),
	//
	.act_vlan_out		(act_vlan_out),
	.act_vlan_out_valid (act_vlan_valid_out),
	.act_vlan_ready		(act_vlan_ready),


	.c_s_axis_tdata		(c_s_axis_tdata_0),
	.c_s_axis_tuser		(c_s_axis_tuser_0),
	.c_s_axis_tkeep		(c_s_axis_tkeep_0),
	.c_s_axis_tvalid	(c_s_axis_tvalid_0),
	.c_s_axis_tlast		(c_s_axis_tlast_0),

	.c_m_axis_tdata		(c_m_axis_tdata),
	.c_m_axis_tuser		(c_m_axis_tuser),
	.c_m_axis_tkeep		(c_m_axis_tkeep),
	.c_m_axis_tvalid	(c_m_axis_tvalid),
	.c_m_axis_tlast		(c_m_axis_tlast)
);



endmodule
