`timescale 1ns / 1ps
module crossbar #(
    parameter STAGE_ID = 0,
    parameter PHV_LEN = 48*8+32*8+16*8+256,
    parameter ACT_LEN = 25,
    parameter width_2B = 16,
    parameter width_4B = 32,
    parameter width_6B = 48
)
(
    input clk,
    input rst_n,

    //input from PHV
    input [PHV_LEN-1:0]         phv_in,
    input                       phv_in_valid,

    //input from action
    input [ACT_LEN*25-1:0]      action_in,
    input                       action_in_valid,
    output reg                  ready_out,

    //output to the ALU
    output reg                    alu_in_valid,
    output reg [width_6B*8-1:0]   alu_in_6B_1,
    output reg [width_6B*8-1:0]   alu_in_6B_2,
    output reg [width_4B*8-1:0]   alu_in_4B_1,
    output reg [width_4B*8-1:0]   alu_in_4B_2,
    output reg [width_4B*8-1:0]   alu_in_4B_3,
    output reg [width_2B*8-1:0]   alu_in_2B_1,
    output reg [width_2B*8-1:0]   alu_in_2B_2,
    output reg [255:0]            phv_remain_data,

    //I have to delay action_in for ALUs for 1 cycle
    output reg [ACT_LEN*25-1:0]   action_out,
    output reg                    action_valid_out,
    input                         ready_in
);

/********intermediate variables declared here********/
integer i;


wire [width_6B-1:0]      cont_6B [0:7];
wire [width_4B-1:0]      cont_4B [0:7];
wire [width_2B-1:0]      cont_2B [0:7];

wire [ACT_LEN-1:0]       sub_action [24:0];


/********intermediate variables declared here********/

assign cont_6B[7] = phv_in[PHV_LEN-1            -: width_6B];
assign cont_6B[6] = phv_in[PHV_LEN-1-  width_6B -: width_6B];
assign cont_6B[5] = phv_in[PHV_LEN-1-2*width_6B -: width_6B];
assign cont_6B[4] = phv_in[PHV_LEN-1-3*width_6B -: width_6B];
assign cont_6B[3] = phv_in[PHV_LEN-1-4*width_6B -: width_6B];
assign cont_6B[2] = phv_in[PHV_LEN-1-5*width_6B -: width_6B];
assign cont_6B[1] = phv_in[PHV_LEN-1-6*width_6B -: width_6B];
assign cont_6B[0] = phv_in[PHV_LEN-1-7*width_6B -: width_6B];

assign cont_4B[7] = phv_in[PHV_LEN-1-8*width_6B           -: width_4B];
assign cont_4B[6] = phv_in[PHV_LEN-1-8*width_6B-  width_4B -: width_4B];
assign cont_4B[5] = phv_in[PHV_LEN-1-8*width_6B-2*width_4B -: width_4B];
assign cont_4B[4] = phv_in[PHV_LEN-1-8*width_6B-3*width_4B -: width_4B];
assign cont_4B[3] = phv_in[PHV_LEN-1-8*width_6B-4*width_4B -: width_4B];
assign cont_4B[2] = phv_in[PHV_LEN-1-8*width_6B-5*width_4B -: width_4B];
assign cont_4B[1] = phv_in[PHV_LEN-1-8*width_6B-6*width_4B -: width_4B];
assign cont_4B[0] = phv_in[PHV_LEN-1-8*width_6B-7*width_4B -: width_4B];


assign cont_2B[7] = phv_in[PHV_LEN-1-8*width_6B-8*width_4B            -: width_2B];
assign cont_2B[6] = phv_in[PHV_LEN-1-8*width_6B-8*width_4B-  width_2B -: width_2B];
assign cont_2B[5] = phv_in[PHV_LEN-1-8*width_6B-8*width_4B-2*width_2B -: width_2B];
assign cont_2B[4] = phv_in[PHV_LEN-1-8*width_6B-8*width_4B-3*width_2B -: width_2B];
assign cont_2B[3] = phv_in[PHV_LEN-1-8*width_6B-8*width_4B-4*width_2B -: width_2B];
assign cont_2B[2] = phv_in[PHV_LEN-1-8*width_6B-8*width_4B-5*width_2B -: width_2B];
assign cont_2B[1] = phv_in[PHV_LEN-1-8*width_6B-8*width_4B-6*width_2B -: width_2B];
assign cont_2B[0] = phv_in[PHV_LEN-1-8*width_6B-8*width_4B-7*width_2B -: width_2B];

// Tao: get action for each PHV container
assign sub_action[24] = action_in[ACT_LEN*25-1-:ACT_LEN];					// 1st action
assign sub_action[23] = action_in[ACT_LEN*25-1 -  ACT_LEN-:ACT_LEN];		// 2nd action
assign sub_action[22] = action_in[ACT_LEN*25-1 -2*ACT_LEN-:ACT_LEN];		// 3rd action
assign sub_action[21] = action_in[ACT_LEN*25-1 -3*ACT_LEN-:ACT_LEN];
assign sub_action[20] = action_in[ACT_LEN*25-1 -4*ACT_LEN-:ACT_LEN];
assign sub_action[19] = action_in[ACT_LEN*25-1 -5*ACT_LEN-:ACT_LEN];
assign sub_action[18] = action_in[ACT_LEN*25-1 -6*ACT_LEN-:ACT_LEN];
assign sub_action[17] = action_in[ACT_LEN*25-1 -7*ACT_LEN-:ACT_LEN];

assign sub_action[16] = action_in[ACT_LEN*25-1 -8*ACT_LEN-:ACT_LEN];
assign sub_action[15] = action_in[ACT_LEN*25-1 -9*ACT_LEN-:ACT_LEN];
assign sub_action[14] = action_in[ACT_LEN*25-1 -10*ACT_LEN-:ACT_LEN];
assign sub_action[13] = action_in[ACT_LEN*25-1 -11*ACT_LEN-:ACT_LEN];
assign sub_action[12] = action_in[ACT_LEN*25-1 -12*ACT_LEN-:ACT_LEN];
assign sub_action[11] = action_in[ACT_LEN*25-1 -13*ACT_LEN-:ACT_LEN];
assign sub_action[10] = action_in[ACT_LEN*25-1 -14*ACT_LEN-:ACT_LEN];
assign sub_action[9] = action_in[ACT_LEN*25-1 -15*ACT_LEN-:ACT_LEN];

assign sub_action[8] = action_in[ACT_LEN*25-1 -16*ACT_LEN-:ACT_LEN];
assign sub_action[7] = action_in[ACT_LEN*25-1 -17*ACT_LEN-:ACT_LEN];
assign sub_action[6] = action_in[ACT_LEN*25-1 -18*ACT_LEN-:ACT_LEN];
assign sub_action[5] = action_in[ACT_LEN*25-1 -19*ACT_LEN-:ACT_LEN];
assign sub_action[4] = action_in[ACT_LEN*25-1 -20*ACT_LEN-:ACT_LEN];
assign sub_action[3] = action_in[ACT_LEN*25-1 -21*ACT_LEN-:ACT_LEN];
assign sub_action[2] = action_in[ACT_LEN*25-1 -22*ACT_LEN-:ACT_LEN];
assign sub_action[1] = action_in[ACT_LEN*25-1 -23*ACT_LEN-:ACT_LEN];

assign sub_action[0] = action_in[ACT_LEN*25-1 -24*ACT_LEN-:ACT_LEN];

//assign inputs for ALUs 

always @(posedge clk) begin
	action_out <= action_in;
	action_valid_out <= action_in_valid;
end

localparam IDLE = 0,
			PROCESS = 1,
			HALT = 2;

reg [2:0] state;

always @(posedge clk or negedge rst_n) begin
    if(~rst_n) begin
        // phv_reg <= 1124'b0;
        // action_full_reg <= 625'b0;
        // phv_valid_reg <= 1'b0;
        // action_valid_reg <= 1'b0;
        //reset outputs
        alu_in_valid <= 1'b0;
        phv_remain_data <= 256'b0;
        //reset all the outputs
        alu_in_6B_1 <= 384'b0;
        alu_in_6B_2 <= 384'b0;
        alu_in_4B_1 <= 256'b0;
        alu_in_4B_2 <= 256'b0;
        alu_in_4B_3 <= 256'b0;
        alu_in_2B_1 <= 128'b0;
        alu_in_2B_2 <= 128'b0;
       
		state <= IDLE;
		ready_out <= 1;
    end

    else begin
		case (state) 
			IDLE: begin

				if(phv_in_valid == 1'b1) begin
					if (ready_in) begin
						alu_in_valid <= 1'b1;
					end
					else begin
						ready_out <= 0;
						state <= HALT;
					end
        		    //assign values one by one (of course need to consider act format)
        		    for(i=7; i>=0; i=i-1) begin
        		        case(sub_action[16+i+1][24:21])
        		            //be noted that 2 ops need to be the same width
        		            4'b0001, 4'b0010: begin
        		                alu_in_6B_1[(i+1)*width_6B-1 -: width_6B] <= cont_6B[sub_action[16+i+1][18:16]];
        		                alu_in_6B_2[(i+1)*width_6B-1 -: width_6B] <= cont_6B[sub_action[16+i+1][13:11]];
        		            end
        		            //extracted from action field (imm)
        		            4'b1001, 4'b1010: begin
        		                alu_in_6B_1[(i+1)*width_6B-1 -: width_6B] <= cont_6B[sub_action[16+i+1][18:16]];
        		                alu_in_6B_2[(i+1)*width_6B-1 -: width_6B] <= {32'b0,sub_action[16+i+1][15:0]};
        		            end
							// set operation, operand A set to 0, operand B set to imm
							4'b1110: begin
        		                alu_in_6B_1[(i+1)*width_6B-1 -: width_6B] <= 48'b0;
        		                alu_in_6B_2[(i+1)*width_6B-1 -: width_6B] <= {32'b0,sub_action[16+i+1][15:0]};
							end
        		            //if there is no action to take, output the original value
        		            default: begin
        		                //alu_1 should be set to the phv value
        		                alu_in_6B_1[(i+1)*width_6B-1 -: width_6B] <= cont_6B[i];
        		                alu_in_6B_2[(i+1)*width_6B-1 -: width_6B] <= 48'b0;
        		            end
        		        endcase
        		    end
        		    //4B is a bit of differernt from 2B and 6B
        		    for(i=7; i>=0; i=i-1) begin
        		        alu_in_4B_3[(i+1)*width_4B-1 -: width_4B] <= cont_4B[i];
        		        casez(sub_action[8+i+1][24:21])
        		            //be noted that 2 ops need to be the same width
        		            4'b0001, 4'b0010: begin
        		                alu_in_4B_1[(i+1)*width_4B-1 -: width_4B] <= cont_4B[sub_action[8+i+1][18:16]];
        		                alu_in_4B_2[(i+1)*width_4B-1 -: width_4B] <= cont_4B[sub_action[8+i+1][13:11]];
        		            end
        		            4'b1001, 4'b1010: begin
        		                alu_in_4B_1[(i+1)*width_4B-1 -: width_4B] <= cont_4B[sub_action[8+i+1][18:16]];
        		                alu_in_4B_2[(i+1)*width_4B-1 -: width_4B] <= {16'b0,sub_action[8+i+1][15:0]};
        		            end
							// set operation, operand A set to 0, operand B set to imm
							4'b1110: begin
        		                alu_in_4B_1[(i+1)*width_4B-1 -: width_4B] <= 32'b0;
        		                alu_in_4B_2[(i+1)*width_4B-1 -: width_4B] <= {16'b0,sub_action[8+i+1][15:0]};
							end
        		            //loadd put here
        		            4'b1011, 4'b1000, 4'b0111: begin
        		                alu_in_4B_1[(i+1)*width_4B-1 -: width_4B] <= cont_4B[sub_action[8+i+1][18:16]];
        		                //alu_in_4B_2[(i+1)*width_4B-1 -: width_4B] <= {16'b0,sub_action[8+i+1][15:0]};
        		                alu_in_4B_2[(i+1)*width_4B-1 -: width_4B] <= cont_4B[sub_action[8+i+1][13:11]];
        		            end
        		            //if there is no action to take, output the original value
        		            default: begin
        		                //alu_1 should be set to the phv value
        		                alu_in_4B_1[(i+1)*width_4B-1 -: width_4B] <= cont_4B[i];
        		                alu_in_4B_2[(i+1)*width_4B-1 -: width_4B] <= 32'b0;
        		            end
        		        endcase
        		    end
        		    for(i=7; i>=0; i=i-1) begin
        		        casez(sub_action[i+1][24:21])
        		            //be noted that 2 ops need to be the same width
        		            4'b0001, 4'b0010: begin
        		                alu_in_2B_1[(i+1)*width_2B-1 -: width_2B] <= cont_2B[sub_action[i+1][18:16]];
        		                alu_in_2B_2[(i+1)*width_2B-1 -: width_2B] <= cont_2B[sub_action[i+1][13:11]];
        		            end
        		            4'b1001, 4'b1010: begin
        		                alu_in_2B_1[(i+1)*width_2B-1 -: width_2B] <= cont_2B[sub_action[i+1][18:16]];
        		                alu_in_2B_2[(i+1)*width_2B-1 -: width_2B] <= sub_action[i+1][15:0];
        		            end
							// set operation, operand A set to 0, operand B set to imm
							4'b1110: begin
        		                alu_in_2B_1[(i+1)*width_2B-1 -: width_2B] <= 16'b0;
        		                alu_in_2B_2[(i+1)*width_2B-1 -: width_2B] <= sub_action[i+1][15:0];
							end
        		            //if there is no action to take, output the original value
        		            default: begin
        		                //alu_1 should be set to the phv value
        		                alu_in_2B_1[(i+1)*width_2B-1 -: width_2B] <= cont_2B[i];
        		                alu_in_2B_2[(i+1)*width_2B-1 -: width_2B] <= 16'b0;
        		            end
        		        endcase
        		    end
        		    
        		    //the left is metadata & conditional ins, no need to modify
        		    phv_remain_data <= phv_in[255:0];
        		end 

        		else begin
        		    alu_in_valid <= 1'b0;
        		end
			end
			HALT: begin
				if (ready_in) begin
					alu_in_valid <= 1'b1;
					state <= IDLE;
					ready_out <= 1'b1;
				end
			end
		endcase
    end
end

endmodule
