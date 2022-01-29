`timescale 1ns / 1ps


module sub_deparser #(
	parameter C_PKT_VEC_WIDTH = (6+4+2)*8*8+256,
	parameter C_PARSE_ACT_LEN = 6						// only 6 bits are used here
)
(
	input										clk,
	input										aresetn,

	input										parse_act_valid,
	input [C_PARSE_ACT_LEN-1:0]					parse_act,
	input [C_PKT_VEC_WIDTH-1:0]					phv_in,

	output reg									val_out_valid,
	output reg [47:0]							val_out,
	output reg [1:0]							val_out_type
);

localparam PHV_2B_START_POS = 0+256;
localparam PHV_4B_START_POS = 16*8+256;
localparam PHV_6B_START_POS = 16*8+32*8+256;


reg			val_out_valid_nxt;
reg [47:0]	val_out_nxt;
reg [1:0]	val_out_type_nxt;


always @(*) begin
	val_out_valid_nxt = 0;
	val_out_nxt = val_out;
	val_out_type_nxt = val_out_type;

	if (parse_act_valid) begin
		val_out_valid_nxt = 1;

		case({parse_act[5:4], parse_act[0]})
			// 2B
			3'b011: begin
				val_out_type_nxt = 2'b01;
				case(parse_act[3:1])
					3'd0: val_out_nxt[15:0] = phv_in[PHV_2B_START_POS+16*0 +: 16];
					3'd1: val_out_nxt[15:0] = phv_in[PHV_2B_START_POS+16*1 +: 16];
					3'd2: val_out_nxt[15:0] = phv_in[PHV_2B_START_POS+16*2 +: 16];
					3'd3: val_out_nxt[15:0] = phv_in[PHV_2B_START_POS+16*3 +: 16];
					3'd4: val_out_nxt[15:0] = phv_in[PHV_2B_START_POS+16*4 +: 16];
					3'd5: val_out_nxt[15:0] = phv_in[PHV_2B_START_POS+16*5 +: 16];
					3'd6: val_out_nxt[15:0] = phv_in[PHV_2B_START_POS+16*6 +: 16];
					3'd7: val_out_nxt[15:0] = phv_in[PHV_2B_START_POS+16*7 +: 16];
				endcase
			end
			// 4B
			3'b101: begin
				val_out_type_nxt = 2'b10;
				case(parse_act[3:1])
					3'd0: val_out_nxt[31:0] = phv_in[PHV_4B_START_POS+32*0 +: 32];
					3'd1: val_out_nxt[31:0] = phv_in[PHV_4B_START_POS+32*1 +: 32];
					3'd2: val_out_nxt[31:0] = phv_in[PHV_4B_START_POS+32*2 +: 32];
					3'd3: val_out_nxt[31:0] = phv_in[PHV_4B_START_POS+32*3 +: 32];
					3'd4: val_out_nxt[31:0] = phv_in[PHV_4B_START_POS+32*4 +: 32];
					3'd5: val_out_nxt[31:0] = phv_in[PHV_4B_START_POS+32*5 +: 32];
					3'd6: val_out_nxt[31:0] = phv_in[PHV_4B_START_POS+32*6 +: 32];
					3'd7: val_out_nxt[31:0] = phv_in[PHV_4B_START_POS+32*7 +: 32];
				endcase
			end
			// 6B
			3'b111: begin
				val_out_type_nxt = 2'b11;
				case(parse_act[3:1])
					3'd0: val_out_nxt[47:0] = phv_in[PHV_6B_START_POS+48*0 +: 48];
					3'd1: val_out_nxt[47:0] = phv_in[PHV_6B_START_POS+48*1 +: 48];
					3'd2: val_out_nxt[47:0] = phv_in[PHV_6B_START_POS+48*2 +: 48];
					3'd3: val_out_nxt[47:0] = phv_in[PHV_6B_START_POS+48*3 +: 48];
					3'd4: val_out_nxt[47:0] = phv_in[PHV_6B_START_POS+48*4 +: 48];
					3'd5: val_out_nxt[47:0] = phv_in[PHV_6B_START_POS+48*5 +: 48];
					3'd6: val_out_nxt[47:0] = phv_in[PHV_6B_START_POS+48*6 +: 48];
					3'd7: val_out_nxt[47:0] = phv_in[PHV_6B_START_POS+48*7 +: 48];
				endcase
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
	end
	else begin
		val_out_valid <= val_out_valid_nxt;
		val_out <= val_out_nxt;
		val_out_type <= val_out_type_nxt;
	end
end

endmodule
