`timescale 1ns / 1ps


module parser_wait_segs #(
	parameter C_AXIS_DATA_WIDTH = 512,
	parameter C_AXIS_TUSER_WIDTH = 128,
	parameter C_NUM_SEGS = 2
)
(
	input											axis_clk,
	input											aresetn,
	
	//
	input [C_AXIS_DATA_WIDTH-1:0]					s_axis_tdata,
	input [C_AXIS_TUSER_WIDTH-1:0]					s_axis_tuser,
	input [C_AXIS_DATA_WIDTH/8-1:0]					s_axis_tkeep,
	input											s_axis_tvalid,
	input											s_axis_tlast,
	
	//
	output reg[C_NUM_SEGS*C_AXIS_DATA_WIDTH-1:0]	tdata_segs,
	output reg[C_AXIS_TUSER_WIDTH-1:0]				tuser_1st,
	output reg										segs_valid
);

localparam	WAIT_1ST_SEG=0,
			WAIT_2ND_SEG=1,
			WAIT_1CYCLE=2,
			OUTPUT_SEGS=3,
			WAIT_TILL_LAST=4;

reg [2:0]	state, state_next;
reg [C_NUM_SEGS*C_AXIS_DATA_WIDTH-1:0] tdata_segs_next;
reg [C_AXIS_TUSER_WIDTH-1:0] tuser_1st_next;
reg	segs_valid_next;

always @(*) begin

	state_next = state;

	tdata_segs_next = tdata_segs;
	tuser_1st_next = tuser_1st;
	segs_valid_next = 0;

	case (state)
		// at-most 2 segs
		WAIT_1ST_SEG: begin
			if (s_axis_tvalid) begin
				tdata_segs_next[0*C_AXIS_DATA_WIDTH+:C_AXIS_DATA_WIDTH] = s_axis_tdata;
				tuser_1st_next = s_axis_tuser;

				if (s_axis_tlast) begin
					state_next = WAIT_1CYCLE;
				end
				else begin
					state_next = WAIT_2ND_SEG;
				end
			end
		end
		WAIT_1CYCLE: begin
			segs_valid_next = 1;
			state_next = WAIT_1ST_SEG;
		end
		WAIT_2ND_SEG: begin
			if (s_axis_tvalid) begin
				tdata_segs_next[1*C_AXIS_DATA_WIDTH+:C_AXIS_DATA_WIDTH] = s_axis_tdata;

				segs_valid_next = 1;
				if (s_axis_tlast) begin
					state_next = WAIT_1ST_SEG;
				end
				else begin
					state_next = WAIT_TILL_LAST;
				end
			end
		end
		WAIT_TILL_LAST: begin
			if (s_axis_tvalid && s_axis_tlast) begin
				state_next = WAIT_1ST_SEG;
			end
		end
	endcase
end


always @(posedge axis_clk) begin
	if (~aresetn) begin

		state <= WAIT_1ST_SEG;

		tdata_segs <= {C_NUM_SEGS*C_AXIS_DATA_WIDTH{1'b0}};
		tuser_1st <= {C_AXIS_TUSER_WIDTH{1'b0}};
		segs_valid <= 0;
	end
	else begin
		state <= state_next;

		tdata_segs <= tdata_segs_next;
		tuser_1st <= tuser_1st_next;

		segs_valid <= segs_valid_next;
	end
end

endmodule
