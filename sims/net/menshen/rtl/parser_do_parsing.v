`timescale 1ns / 1ps

`define DEF_MAC_ADDR	48
`define DEF_VLAN		32
`define DEF_ETHTYPE		16

`define TYPE_IPV4		16'h0008
`define TYPE_ARP		16'h0608

`define PROT_ICMP		8'h01
`define PROT_TCP		8'h06
`define PROT_UDP		8'h11

`define SUB_PARSE(idx) \
	case(sub_parse_val_out_type_d1[idx]) \
		2'b01: val_2B_nxt[sub_parse_val_out_seq_d1[idx]] = sub_parse_val_out_d1[idx][15:0]; \
		2'b10: val_4B_nxt[sub_parse_val_out_seq_d1[idx]] = sub_parse_val_out_d1[idx][31:0]; \
		2'b11: val_6B_nxt[sub_parse_val_out_seq_d1[idx]] = sub_parse_val_out_d1[idx][47:0]; \
	endcase \

`define SWAP_BYTE_ORDER(idx) \
	assign val_6B_swapped[idx] = {	val_6B[idx][0+:8], \
									val_6B[idx][8+:8], \
									val_6B[idx][16+:8], \
									val_6B[idx][24+:8], \
									val_6B[idx][32+:8], \
									val_6B[idx][40+:8]}; \
	assign val_4B_swapped[idx] = {	val_4B[idx][0+:8], \
									val_4B[idx][8+:8], \
									val_4B[idx][16+:8], \
									val_4B[idx][24+:8]}; \
	assign val_2B_swapped[idx] = {	val_2B[idx][0+:8], \
									val_2B[idx][8+:8]}; \

module parser_do_parsing #(
	parameter C_AXIS_DATA_WIDTH = 512,
	parameter C_AXIS_TUSER_WIDTH = 128,
	parameter PKT_HDR_LEN = (6+4+2)*8*8+256, // check with the doc
	parameter PARSER_MOD_ID = 3'b0,
	parameter C_NUM_SEGS = 2,
	parameter C_VLANID_WIDTH = 12,
	parameter C_PARSER_RAM_WIDTH = 160
)
(
	input											axis_clk,
	input											aresetn,

	input [C_NUM_SEGS*C_AXIS_DATA_WIDTH-1:0]		tdata_segs,
	input [C_AXIS_TUSER_WIDTH-1:0]					tuser_1st,
	input											segs_valid,
	input [C_PARSER_RAM_WIDTH-1:0]					bram_in,
	input											bram_in_valid,


	input											stg_ready_in,

	// phv output
	output reg										parser_valid,
	output reg [PKT_HDR_LEN-1:0]					pkt_hdr_vec,
	// vlan output
	output reg [C_VLANID_WIDTH-1:0]					vlan_out,
	output reg										vlan_out_valid
);

integer i;

localparam			IDLE=0,
					WAIT_1CYCLE_RAM=1,
					START_SUB_PARSE=2,
					FINISH_SUB_PARSE=3,
					GET_PHV_OUTPUT=4,
					OUTPUT=5,
					EMPTY_1=6;
					

//
reg [PKT_HDR_LEN-1:0]	pkt_hdr_vec_next;
reg parser_valid_next;
reg [3:0] state, state_next;
reg [11:0] vlan_out_next;
reg vlan_out_valid_next;

// parsing actions
wire [15:0] parse_action [0:9];		// we have 10 parse action

assign parse_action[9] = bram_in[0+:16];
assign parse_action[8] = bram_in[16+:16];
assign parse_action[7] = bram_in[32+:16];
assign parse_action[6] = bram_in[48+:16];
assign parse_action[5] = bram_in[64+:16];
assign parse_action[4] = bram_in[80+:16];
assign parse_action[3] = bram_in[96+:16];
assign parse_action[2] = bram_in[112+:16];
assign parse_action[1] = bram_in[128+:16];
assign parse_action[0] = bram_in[144+:16];


reg [9:0] sub_parse_act_valid;
wire [47:0] sub_parse_val_out [0:9];
wire [9:0] sub_parse_val_out_valid;
wire [1:0] sub_parse_val_out_type [0:9];
wire [2:0] sub_parse_val_out_seq [0:9];

reg [47:0] sub_parse_val_out_d1 [0:9];
reg [9:0] sub_parse_val_out_valid_d1;
reg [1:0] sub_parse_val_out_type_d1 [0:9];
reg [2:0] sub_parse_val_out_seq_d1 [0:9];

reg [47:0] val_6B [0:7];
reg [31:0] val_4B [0:7];
reg [15:0] val_2B [0:7];
reg [47:0] val_6B_nxt [0:7];
reg [31:0] val_4B_nxt [0:7];
reg [15:0] val_2B_nxt [0:7];

wire [47:0] val_6B_swapped [0:7];
wire [31:0] val_4B_swapped [0:7];
wire [15:0] val_2B_swapped [0:7];

`SWAP_BYTE_ORDER(0)
`SWAP_BYTE_ORDER(1)
`SWAP_BYTE_ORDER(2)
`SWAP_BYTE_ORDER(3)
`SWAP_BYTE_ORDER(4)
`SWAP_BYTE_ORDER(5)
`SWAP_BYTE_ORDER(6)
`SWAP_BYTE_ORDER(7)

always @(*) begin
	state_next = state;
	//
	parser_valid_next = 0;
	pkt_hdr_vec_next = pkt_hdr_vec;
	//
	val_2B_nxt[0]=val_2B[0];
	val_2B_nxt[1]=val_2B[1];
	val_2B_nxt[2]=val_2B[2];
	val_2B_nxt[3]=val_2B[3];
	val_2B_nxt[4]=val_2B[4];
	val_2B_nxt[5]=val_2B[5];
	val_2B_nxt[6]=val_2B[6];
	val_2B_nxt[7]=val_2B[7];
	val_4B_nxt[0]=val_4B[0];
	val_4B_nxt[1]=val_4B[1];
	val_4B_nxt[2]=val_4B[2];
	val_4B_nxt[3]=val_4B[3];
	val_4B_nxt[4]=val_4B[4];
	val_4B_nxt[5]=val_4B[5];
	val_4B_nxt[6]=val_4B[6];
	val_4B_nxt[7]=val_4B[7];
	val_6B_nxt[0]=val_6B[0];
	val_6B_nxt[1]=val_6B[1];
	val_6B_nxt[2]=val_6B[2];
	val_6B_nxt[3]=val_6B[3];
	val_6B_nxt[4]=val_6B[4];
	val_6B_nxt[5]=val_6B[5];
	val_6B_nxt[6]=val_6B[6];
	val_6B_nxt[7]=val_6B[7];
	//
	sub_parse_act_valid = 10'b0;
	//
	vlan_out_next = vlan_out;
	vlan_out_valid_next = 0;

	case (state)
		IDLE: begin
			if (segs_valid) begin
				sub_parse_act_valid = 10'b1111111111;
				vlan_out_next = tdata_segs[116+:12];
				state_next = FINISH_SUB_PARSE;
			end
		end
		FINISH_SUB_PARSE: begin
			state_next = EMPTY_1;
		end
		EMPTY_1: begin
			state_next = GET_PHV_OUTPUT;
			`SUB_PARSE(0)
			`SUB_PARSE(1)
			`SUB_PARSE(2)
			`SUB_PARSE(3)
			`SUB_PARSE(4)
			`SUB_PARSE(5)
			`SUB_PARSE(6)
			`SUB_PARSE(7)
			`SUB_PARSE(8)
			`SUB_PARSE(9)
			vlan_out_valid_next = 1;
		end
		GET_PHV_OUTPUT: begin
			pkt_hdr_vec_next ={val_6B_swapped[7], val_6B_swapped[6], val_6B_swapped[5], val_6B_swapped[4], val_6B_swapped[3], val_6B_swapped[2], val_6B_swapped[1], val_6B_swapped[0],
							val_4B_swapped[7], val_4B_swapped[6], val_4B_swapped[5], val_4B_swapped[4], val_4B_swapped[3], val_4B_swapped[2], val_4B_swapped[1], val_4B_swapped[0],
							val_2B_swapped[7], val_2B_swapped[6], val_2B_swapped[5], val_2B_swapped[4], val_2B_swapped[3], val_2B_swapped[2], val_2B_swapped[1], val_2B_swapped[0],
							// Tao: manually set output port to 1 for eazy test
							// {115{1'b0}}, vlan_id, 1'b0, tuser_1st[127:32], 8'h04, tuser_1st[23:0]};
							{115{1'b0}}, vlan_out, 1'b0, tuser_1st[127:0]};
							// {115{1'b0}}, vlan_id, 1'b0, tuser_1st};
							// {128{1'b0}}, tuser_1st[127:32], 8'h04, tuser_1st[23:0]};
							//
			if (stg_ready_in) begin
				parser_valid_next = 1;
				state_next = IDLE;
			end
			else begin
				state_next = OUTPUT;
			end
		end
		OUTPUT: begin
			if (stg_ready_in) begin
				parser_valid_next = 1;
				state_next = IDLE;
				
				// zero out
				val_2B_nxt[0]=0;
				val_2B_nxt[1]=0;
				val_2B_nxt[2]=0;
				val_2B_nxt[3]=0;
				val_2B_nxt[4]=0;
				val_2B_nxt[5]=0;
				val_2B_nxt[6]=0;
				val_2B_nxt[7]=0;
				val_4B_nxt[0]=0;
				val_4B_nxt[1]=0;
				val_4B_nxt[2]=0;
				val_4B_nxt[3]=0;
				val_4B_nxt[4]=0;
				val_4B_nxt[5]=0;
				val_4B_nxt[6]=0;
				val_4B_nxt[7]=0;
				val_6B_nxt[0]=0;
				val_6B_nxt[1]=0;
				val_6B_nxt[2]=0;
				val_6B_nxt[3]=0;
				val_6B_nxt[4]=0;
				val_6B_nxt[5]=0;
				val_6B_nxt[6]=0;
				val_6B_nxt[7]=0;
			end
		end
	endcase
end



always @(posedge axis_clk) begin
	if (~aresetn) begin
		state <= IDLE;
		//
		pkt_hdr_vec <= 0;
		parser_valid <= 0;
		//
		vlan_out <= 0;
		vlan_out_valid <= 0;
		//
		val_2B[0] <= 0;
		val_2B[1] <= 0;
		val_2B[2] <= 0;
		val_2B[3] <= 0;
		val_2B[4] <= 0;
		val_2B[5] <= 0;
		val_2B[6] <= 0;
		val_2B[7] <= 0;
		val_4B[0] <= 0;
		val_4B[1] <= 0;
		val_4B[2] <= 0;
		val_4B[3] <= 0;
		val_4B[4] <= 0;
		val_4B[5] <= 0;
		val_4B[6] <= 0;
		val_4B[7] <= 0;
		val_6B[0] <= 0;
		val_6B[1] <= 0;
		val_6B[2] <= 0;
		val_6B[3] <= 0;
		val_6B[4] <= 0;
		val_6B[5] <= 0;
		val_6B[6] <= 0;
		val_6B[7] <= 0;

		for (i=0; i<10; i=i+1) begin
			sub_parse_val_out_d1[i] <= 0;
			sub_parse_val_out_valid_d1 <= 0;
			sub_parse_val_out_type_d1[i] <= 0;
			sub_parse_val_out_seq_d1[i] <= 0 ;
		end
	end
	else begin
		state <= state_next;
		//
		pkt_hdr_vec <= pkt_hdr_vec_next;
		parser_valid <= parser_valid_next;
		//
		vlan_out <= vlan_out_next;
		vlan_out_valid <= vlan_out_valid_next;
		//
		val_2B[0] <= val_2B_nxt[0];
		val_2B[1] <= val_2B_nxt[1];
		val_2B[2] <= val_2B_nxt[2];
		val_2B[3] <= val_2B_nxt[3];
		val_2B[4] <= val_2B_nxt[4];
		val_2B[5] <= val_2B_nxt[5];
		val_2B[6] <= val_2B_nxt[6];
		val_2B[7] <= val_2B_nxt[7];
		val_4B[0] <= val_4B_nxt[0];
		val_4B[1] <= val_4B_nxt[1];
		val_4B[2] <= val_4B_nxt[2];
		val_4B[3] <= val_4B_nxt[3];
		val_4B[4] <= val_4B_nxt[4];
		val_4B[5] <= val_4B_nxt[5];
		val_4B[6] <= val_4B_nxt[6];
		val_4B[7] <= val_4B_nxt[7];
		val_6B[0] <= val_6B_nxt[0];
		val_6B[1] <= val_6B_nxt[1];
		val_6B[2] <= val_6B_nxt[2];
		val_6B[3] <= val_6B_nxt[3];
		val_6B[4] <= val_6B_nxt[4];
		val_6B[5] <= val_6B_nxt[5];
		val_6B[6] <= val_6B_nxt[6];
		val_6B[7] <= val_6B_nxt[7];
		//
		for (i=0; i<10; i=i+1) begin
			sub_parse_val_out_d1[i] <= sub_parse_val_out[i];
			sub_parse_val_out_valid_d1 <= sub_parse_val_out_valid;
			sub_parse_val_out_type_d1[i] <= sub_parse_val_out_type[i];
			sub_parse_val_out_seq_d1[i] <= sub_parse_val_out_seq[i];
		end
	end
end

// =============================================================== //
// sub parser
generate
	genvar index;
	for (index=0; index<10; index=index+1) begin:
		sub_op
		sub_parser #(
			.PKTS_HDR_LEN(),
			.PARSE_ACT_LEN(),
			.VAL_OUT_LEN()
		)
		sub_parser (
			.clk				(axis_clk),
			.aresetn			(aresetn),

			.parse_act_valid	(sub_parse_act_valid[index]),
			.parse_act			(parse_action[index]),

			.pkts_hdr			(tdata_segs),
			.val_out_valid		(sub_parse_val_out_valid[index]),
			.val_out			(sub_parse_val_out[index]),
			.val_out_type		(sub_parse_val_out_type[index]),
			.val_out_seq		(sub_parse_val_out_seq[index])
		);
	end
endgenerate


endmodule


