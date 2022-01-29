`timescale 1ns / 1ps



module sub_parser #(
	parameter PKTS_HDR_LEN = 1024,
	parameter PARSE_ACT_LEN = 16,
	parameter VAL_OUT_LEN = 48
)
(
	input				clk,
	input				aresetn,

	input						parse_act_valid,
	input [PARSE_ACT_LEN-1:0]	parse_act,

	input [PKTS_HDR_LEN-1:0]	pkts_hdr,

	output reg					val_out_valid,
	output reg [VAL_OUT_LEN-1:0]	val_out,
	output reg [1:0]			val_out_type,
	output reg [2:0]			val_out_seq
);


reg [VAL_OUT_LEN-1:0]		val_out_nxt;
reg							val_out_valid_nxt;
reg [1:0]					val_out_type_nxt;
reg [2:0]					val_out_seq_nxt;

always @(*) begin
	val_out_valid_nxt = 0;
	val_out_nxt = val_out;
	val_out_type_nxt = val_out_type;
	val_out_seq_nxt = val_out_seq;

	if (parse_act_valid) begin
		val_out_valid_nxt = 1;
		val_out_seq_nxt = parse_act[3:1];
		
		case({parse_act[5:4], parse_act[0]})
			// 2B
			3'b011: begin
				val_out_type_nxt = 2'b01;
				val_out_nxt[15:0] = pkts_hdr[(parse_act[12:6])*8 +: 16];
			end
			// 4B
			3'b101: begin
				val_out_type_nxt = 2'b10;
				val_out_nxt[31:0] = pkts_hdr[(parse_act[12:6])*8 +: 32];
			end
			// 6B
			3'b111: begin
				val_out_type_nxt = 2'b11;
				val_out_nxt[47:0] = pkts_hdr[(parse_act[12:6])*8 +: 48];
			end
			default: begin
				val_out_type_nxt = 0;
				val_out_nxt = 0;
			end
		endcase
	end
end

always @(posedge clk) begin
	if (~aresetn) begin
		val_out_valid <= 0;
		val_out <= 0;
		val_out_type <= 0;
		val_out_seq <= 0;
	end
	else begin
		val_out_valid <= val_out_valid_nxt;
		val_out <= val_out_nxt;
		val_out_type <= val_out_type_nxt;
		val_out_seq <= val_out_seq_nxt;
	end
end


endmodule
