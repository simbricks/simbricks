`timescale 1ns / 1ps

module alu_1 #(
    parameter STAGE_ID = 0,
    parameter ACTION_LEN = 25,
    parameter DATA_WIDTH = 48  //data width of the ALU
)
(
    input clk,
    input rst_n,

    //input from sub_action
    input [ACTION_LEN-1:0]            action_in,
    input                             action_valid,
    input [DATA_WIDTH-1:0]            operand_1_in,
    input [DATA_WIDTH-1:0]            operand_2_in,

    //output to form PHV
    output reg [DATA_WIDTH-1:0]       container_out,
    output reg                        container_out_valid

);

/*
4 operations to support:

1,2. add/sub:   0001/0010
              extract 2 operands from pkt header, add(sub) and write back.

3,4. addi/subi: 0011/0100
              extract op1 from pkt header, op2 from action, add(sub) and write back.
*/


localparam IDLE_S=3'd0, 
		   WAIT1_S=3'd1, 
		   WAIT2_S=3'd2, 
		   WAIT3_S=3'd3, 
		   OUTPUT_S=3'd4;

reg [2:0]					state, state_next;
reg [DATA_WIDTH-1:0]		container_out_r;
reg							container_out_valid_next;

always @(*) begin
	state_next = state;
	container_out_r = container_out;
	container_out_valid_next = 0;

	case (state)
		IDLE_S: begin
			if (action_valid) begin
				state_next = OUTPUT_S;
				case(action_in[24:21])
            	    4'b0001, 4'b1001: begin
            	        container_out_r = operand_1_in + operand_2_in;
            	    end
            	    4'b0010, 4'b1010: begin
            	        container_out_r = operand_1_in - operand_2_in;
            	    end
					4'b1110: begin
						container_out_r = operand_2_in;
					end
            	    //if its an empty (default) action
            	    default: begin
            	        container_out_r = operand_1_in;
            	    end
            	endcase
			end
		end
		WAIT1_S: begin
			// empty cycle
			state_next = WAIT2_S;
		end
		WAIT2_S: begin
			state_next = WAIT3_S;
		end
		WAIT3_S: begin
			state_next = OUTPUT_S;
		end
		OUTPUT_S: begin
			container_out_valid_next = 1;
			state_next = IDLE_S;
		end
	endcase
end

always @(posedge clk or negedge rst_n) begin
	if (~rst_n) begin
		container_out <= 0;
		container_out_valid <= 0;
		state <= IDLE_S;
	end
	else begin
		state <= state_next;
		container_out_valid <= container_out_valid_next;
		container_out <= container_out_r;
	end
end


endmodule
