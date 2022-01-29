`timescale 1ns / 1ps



module parser_do_parsing_top #(
	parameter C_AXIS_DATA_WIDTH = 512,
	parameter C_AXIS_TUSER_WIDTH = 128,
	parameter PKT_HDR_LEN = (6+4+2)*8*8+256, // check with the doc
	parameter C_NUM_SEGS = 2,
	parameter C_PARSER_RAM_WIDTH = 160,
	parameter C_VLANID_WIDTH = 12
)
(
	input					clk,
	input					aresetn,

	input [C_NUM_SEGS*C_AXIS_DATA_WIDTH-1:0]	segs_in,
	input										segs_in_valid,
	input [C_AXIS_TUSER_WIDTH-1:0]				tuser_1st_in,
	input [C_PARSER_RAM_WIDTH-1:0]				bram_in,
	input										bram_in_valid,

	input										stg_ready,
	input										stg_vlan_ready,

	// phv output
	output reg [PKT_HDR_LEN-1:0]					pkt_hdr_vec,
	output reg										parser_valid,
	output reg [C_VLANID_WIDTH-1:0]					vlan_out,
	output reg										vlan_out_valid
);

wire [C_NUM_SEGS*C_AXIS_DATA_WIDTH-1:0]			sub_parser_segs_in [0:1];
wire											sub_parser_segs_in_valid [0:1];
wire [C_AXIS_TUSER_WIDTH-1:0]					sub_parser_tuser_1st_in [0:1];
wire [C_PARSER_RAM_WIDTH-1:0]					sub_parser_bram_in [0:1];
wire											sub_parser_bram_in_valid [0:1];

reg [1:0] cur_queue, cur_queue_next;
wire [1:0] cur_queue_plus1;

assign cur_queue_plus1 = (cur_queue==1)?0:cur_queue+1;


assign sub_parser_segs_in[0] = segs_in;
assign sub_parser_segs_in[1] = segs_in;
// assign sub_parser_segs_in[2] = segs_in;
// assign sub_parser_segs_in[3] = segs_in;
assign sub_parser_segs_in_valid[0] = (cur_queue==0)?segs_in_valid:0;
assign sub_parser_segs_in_valid[1] = (cur_queue==1)?segs_in_valid:0;
// assign sub_parser_segs_in_valid[2] = (cur_queue==2)?segs_in_valid:0;
// assign sub_parser_segs_in_valid[3] = (cur_queue==3)?segs_in_valid:0;
assign sub_parser_tuser_1st_in[0] = tuser_1st_in;
assign sub_parser_tuser_1st_in[1] = tuser_1st_in;
// assign sub_parser_tuser_1st_in[2] = tuser_1st_in;
// assign sub_parser_tuser_1st_in[3] = tuser_1st_in;

assign sub_parser_bram_in[0] = bram_in;
assign sub_parser_bram_in[1] = bram_in;
// assign sub_parser_bram_in[2] = bram_in;
// assign sub_parser_bram_in[3] = bram_in;
assign sub_parser_bram_in_valid[0] = (cur_queue==0)?bram_in_valid:0;
assign sub_parser_bram_in_valid[1] = (cur_queue==1)?bram_in_valid:0;
// assign sub_parser_bram_in_valid[2] = (cur_queue==2)?bram_in_valid:0;
// assign sub_parser_bram_in_valid[3] = (cur_queue==3)?bram_in_valid:0;



always @(*) begin
	cur_queue_next = cur_queue;
	if (segs_in_valid) begin
		cur_queue_next = cur_queue_plus1;
	end
end

always @(posedge clk) begin
	if (~aresetn) begin
		cur_queue <= 0;
	end
	else begin
		cur_queue <= cur_queue_next;
	end
end

wire [1:0]					nearly_full;
wire [1:0]					empty;
wire [1:0]					vlan_nearly_full;
wire [1:0]					vlan_empty;
wire [PKT_HDR_LEN-1:0]		sub_parser_pkt_hdr_out [0:1];
wire [1:0]					sub_parser_pkt_hdr_valid;
wire [C_VLANID_WIDTH-1:0]	sub_parser_vlan_out [0:1];
wire [1:0]					sub_parser_vlan_out_valid;

reg [PKT_HDR_LEN-1:0]		sub_parser_pkt_hdr_out_d1 [0:1];
reg [1:0]					sub_parser_pkt_hdr_valid_d1;
reg [C_VLANID_WIDTH-1:0]	sub_parser_vlan_out_d1 [0:1];
reg [1:0]					sub_parser_vlan_out_valid_d1;

generate
	genvar i;
	for (i=0; i<2; i=i+1) begin:
		sub_do_parsing
		parser_do_parsing #(
			.C_AXIS_DATA_WIDTH(C_AXIS_DATA_WIDTH),
			.C_AXIS_TUSER_WIDTH(C_AXIS_TUSER_WIDTH)
		)
		phv_do_parsing (
			.axis_clk			(clk),
			.aresetn			(aresetn),
			.tdata_segs			(sub_parser_segs_in[i]),
			.tuser_1st			(sub_parser_tuser_1st_in[i]),
			.segs_valid			(sub_parser_segs_in_valid[i]),

			.bram_in			(sub_parser_bram_in[i]),
			.bram_in_valid		(sub_parser_bram_in_valid[i]),
			.stg_ready_in		(1'b1),
			// output
			.parser_valid		(sub_parser_pkt_hdr_valid[i]),
			.pkt_hdr_vec		(sub_parser_pkt_hdr_out[i]),
			.vlan_out			(sub_parser_vlan_out[i]),
			.vlan_out_valid		(sub_parser_vlan_out_valid[i])
		);
	end
endgenerate

reg [1:0] out_cur_queue, out_cur_queue_next;
wire [1:0] out_cur_queue_plus1;
reg [PKT_HDR_LEN-1:0] pkt_hdr_vec_next;
reg parser_valid_next;

assign out_cur_queue_plus1 = (out_cur_queue==1)?0:out_cur_queue+1;

always @(*) begin
	pkt_hdr_vec_next = pkt_hdr_vec;
	parser_valid_next = 0;
	
	out_cur_queue_next = out_cur_queue;

	if (sub_parser_pkt_hdr_valid_d1[out_cur_queue]) begin
		pkt_hdr_vec_next = sub_parser_pkt_hdr_out_d1[out_cur_queue];
		parser_valid_next = 1;
		out_cur_queue_next = out_cur_queue_plus1;
	end
end

always @(posedge clk) begin
	if (~aresetn) begin
		out_cur_queue <= 0;
		pkt_hdr_vec <= 0;
		parser_valid <= 0;
	end
	else begin
		out_cur_queue <= out_cur_queue_next;
		pkt_hdr_vec <= pkt_hdr_vec_next;
		parser_valid <= parser_valid_next;
	end
end

reg [1:0] vlan_out_cur_queue, vlan_out_cur_queue_next;
wire [1:0] vlan_out_cur_queue_plus1;
reg [C_VLANID_WIDTH-1:0] vlan_out_next;
reg vlan_out_valid_next;

assign vlan_out_cur_queue_plus1 = (vlan_out_cur_queue==1)?0:vlan_out_cur_queue+1;

always @(*) begin
	vlan_out_next = vlan_out;
	vlan_out_valid_next = 0;

	vlan_out_cur_queue_next = vlan_out_cur_queue;

	if (sub_parser_vlan_out_valid_d1[vlan_out_cur_queue]) begin
		vlan_out_next = sub_parser_vlan_out_d1[vlan_out_cur_queue];
		vlan_out_valid_next = 1;
		vlan_out_cur_queue_next = vlan_out_cur_queue_plus1;
	end
end

always @(posedge clk) begin
	if (~aresetn) begin
		vlan_out_cur_queue <= 0;
		vlan_out <= 0;
		vlan_out_valid <= 0;
	end
	else begin
		vlan_out_cur_queue <= vlan_out_cur_queue_next;
		vlan_out <= vlan_out_next;
		vlan_out_valid <= vlan_out_valid_next;
	end
end

always @(posedge clk) begin
	if (~aresetn) begin
		sub_parser_pkt_hdr_out_d1[0] <= 0;
		sub_parser_pkt_hdr_out_d1[1] <= 0;
		sub_parser_pkt_hdr_valid_d1 <= 0;
		sub_parser_vlan_out_d1[0] <= 0;
		sub_parser_vlan_out_d1[1] <= 0;
		sub_parser_vlan_out_valid_d1 <= 0;
	end
	else begin
		sub_parser_pkt_hdr_out_d1[0] <= sub_parser_pkt_hdr_out[0];
		sub_parser_pkt_hdr_out_d1[1] <= sub_parser_pkt_hdr_out[1];
		sub_parser_pkt_hdr_valid_d1 <= sub_parser_pkt_hdr_valid;
		sub_parser_vlan_out_d1[0] <= sub_parser_vlan_out[0];
		sub_parser_vlan_out_d1[1] <= sub_parser_vlan_out[1];
		sub_parser_vlan_out_valid_d1 <= sub_parser_vlan_out_valid;
	end
end


/*
generate
	for (i=0; i<2; i=i+1) begin:
		out_arb_queues
		fallthrough_small_fifo #(
			.WIDTH(PKT_HDR_LEN),
			.MAX_DEPTH_BITS(4)
		) out_arb_fifo (
			.dout			(fifo_pkt_hdr_out[i]),
			.rd_en			(fifo_rd_en[i]),

			.din			(sub_parser_pkt_hdr_out[i]),
			.wr_en			(sub_parser_pkt_hdr_valid[i] & ~nearly_full[i]),

			.full			(),
			.nearly_full	(nearly_full[i]),
			.empty			(empty[i]),
			.reset			(~aresetn),
			.clk			(clk)
		);
	end
	// vlan queue
	for (i=0; i<2; i=i+1) begin:
		vlan_out_arb_queues
		fallthrough_small_fifo #(
			.WIDTH(C_VLANID_WIDTH),
			.MAX_DEPTH_BITS(4)
		) vlan_out_arb_fifo (
			.dout			(fifo_vlan_out[i]),
			.rd_en			(fifo_vlan_rd_en[i]),

			.din			(sub_parser_vlan_out[i]),
			.wr_en			(sub_parser_vlan_out_valid[i] & ~vlan_nearly_full[i]),

			.full			(),
			.nearly_full	(vlan_nearly_full[i]),
			.empty			(vlan_empty[i]),
			.reset			(~aresetn),
			.clk			(clk)
		);
	end
endgenerate


localparam	IDLE=0;

reg [1:0] out_cur_queue, out_cur_queue_next;
wire [1:0] out_cur_queue_plus1;
reg [1:0] vlan_out_cur_queue, vlan_out_cur_queue_next;
wire [1:0] vlan_out_cur_queue_plus1;

assign out_cur_queue_plus1 = (out_cur_queue==1)?0:out_cur_queue+1;
assign vlan_out_cur_queue_plus1 = (vlan_out_cur_queue==1)?0:vlan_out_cur_queue+1;

assign pkt_hdr_vec = fifo_pkt_hdr_out[out_cur_queue];
assign parser_valid = ~empty[out_cur_queue];
assign parser_ready = ~nearly_full[0] ||
						~nearly_full[1];
						// ~nearly_full[2] ||
						// ~nearly_full[3];
assign vlan_out = fifo_vlan_out[vlan_out_cur_queue];
assign vlan_out_valid = ~vlan_empty[vlan_out_cur_queue];

always @(*) begin

	out_cur_queue_next = out_cur_queue;
	fifo_rd_en = 0;

	if (!empty[out_cur_queue]) begin
		if (stg_ready) begin
			fifo_rd_en[out_cur_queue] = 1;
			out_cur_queue_next = out_cur_queue_plus1;
		end
	end
end

always @(*) begin

	vlan_out_cur_queue_next = vlan_out_cur_queue;
	fifo_vlan_rd_en = 0;

	if (!vlan_empty[vlan_out_cur_queue]) begin
		if (stg_vlan_ready) begin
			fifo_vlan_rd_en[out_cur_queue] = 1;
			vlan_out_cur_queue_next = vlan_out_cur_queue_plus1;
		end
	end
end

always @(posedge clk) begin
	if (~aresetn) begin
		out_cur_queue <= 0;
		vlan_out_cur_queue <= 0;
	end
	else begin
		out_cur_queue <= out_cur_queue_next;
		vlan_out_cur_queue <= vlan_out_cur_queue_next;
	end
end*/

endmodule
