`timescale 1ns / 1ps

module alu_2 #(
    parameter STAGE_ID = 0,
    parameter ACTION_LEN = 25,
    parameter DATA_WIDTH = 32,  //data width of the ALU
    parameter ACTION_ID = 3,

	parameter C_S_AXIS_DATA_WIDTH = 512,
	parameter C_S_AXIS_TUSER_WIDTH = 128
)
(
    input clk,
    input rst_n,

    //input from sub_action
    input [ACTION_LEN-1:0]            action_in,
    input                             action_valid,
    input [DATA_WIDTH-1:0]            operand_1_in,
    input [DATA_WIDTH-1:0]            operand_2_in,
    input [DATA_WIDTH-1:0]            operand_3_in,
	output reg 						  ready_out,

	input [15:0]						page_tbl_out,
	input								page_tbl_out_valid,

    //output to form PHV
    output [DATA_WIDTH-1:0]				container_out_w,
    output reg							container_out_valid,
	input								ready_in

);

reg  [3:0]           action_type, action_type_next;

//regs for RAM access
reg                         store_en, store_en_next;
reg  [4:0]                  store_addr, store_addr_next;
wire [31:0]					store_din_w;
reg  [31:0]                 store_din, store_din_next;

wire [31:0]                 load_data;
wire [4:0]					load_addr;
// reg [4:0]                  load_addr, load_addr_next;

reg  [2:0]                  alu_state, alu_state_next;
reg [DATA_WIDTH-1:0]		container_out, container_out_next;
reg							container_out_valid_next;

//regs/wires for isolation
wire [7:0]                  base_addr;
wire [7:0]                  addr_len;

assign {addr_len, base_addr} = page_tbl_out;

reg                         overflow, overflow_next;
reg 						ready_out_next;


/********intermediate variables declared here********/

//support tenant isolation
// assign load_addr = store_addr[4:0] + base_addr;
assign load_addr = operand_2_in[4:0] + base_addr;

assign store_din_w = (action_type==4'b1000)?store_din:
						((action_type==4'b0111)?(load_data+1):0);

assign container_out_w = (action_type==4'b1011)?load_data:
							(action_type==4'b0111)?(load_data+1):
							container_out;

/*
7 operations to support:

1,2. add/sub:   0001/0010
              extract 2 operands from pkt header, add(sub) and write back.

3,4. addi/subi: 1001/1010
              extract op1 from pkt header, op2 from action, add(sub) and write back.

5: load:      0101
              load data from RAM, write to pkt header according to addr in action.

6. store:     0110
              read data from pkt header, write to ram according to addr in action.

7. loadd:     0111
              load data from RAM, increment by 1 write it to container, and write it
              back to the RAM. 
8. set:		  1110
			  set to an immediate value
*/

localparam  IDLE_S = 3'd0,
            EMPTY1_S = 3'd1,
            OB_ADDR_S = 3'd2,
            EMPTY2_S = 3'd3,
            OUTPUT_S = 3'd4,
			HALT_S = 3'd5;

always @(*) begin
	alu_state_next = alu_state;

	action_type_next = action_type;
	container_out_next = container_out;

	store_addr_next = store_addr;
	store_din_next = store_din;
	store_en_next = 0;
	// load_addr_next = load_addr;
    overflow_next = overflow;

	container_out_valid_next = 0;

	ready_out_next = ready_out;
	
	case (alu_state)
		IDLE_S: begin
			
            if (action_valid) begin
				action_type_next = action_in[24:21];
                overflow_next = 0;
				alu_state_next = EMPTY1_S;
				ready_out_next = 1'b0;

                
                case(action_in[24:21])
                    //add/addi ops 
                    4'b0001, 4'b1001: begin
                        container_out_next = operand_1_in + operand_2_in;
                    end 
                    //sub/subi ops
                    4'b0010, 4'b1010: begin
                        container_out_next = operand_1_in - operand_2_in;
                    end
                    //store op (interact with RAM)
                    4'b1000: begin
                        container_out_next = operand_3_in;
                        //store_en_r = 1;
                        store_addr_next = operand_2_in[4:0];
                        store_din_next = operand_1_in;
                    end
                    // load op (interact with RAM)
                    4'b1011: begin
                        container_out_next = operand_3_in;
                    end
					// loadd op
                    4'b0111: begin
                        // do nothing now
                        //checkme
                        container_out_next = operand_3_in;
                        store_addr_next = operand_2_in[4:0];
                    end
					// set operation
					4'b1110: begin
						container_out_next = operand_2_in;
					end
                    //cannot go back to IDLE since this
                    //might be a legal action.
                    default: begin
                        container_out_next = operand_3_in;
                    end
				endcase

				//ok, if its `load` op, needs to check overflow.
            	if(action_in[24:21] == 4'b1011 || action_in[24:21] == 4'b0111 || action_in[24:21] == 4'b1000) begin
            	    if(operand_2_in[4:0] > addr_len) begin
            	        overflow_next = 1'b1;
            	    end
            	    else begin
            	        overflow_next = 1'b0;
            	        //its the right time to write for `store`
            	        if(action_in[24:21] == 4'b1000 || action_in[24:21] == 4'b0111) begin
            	            store_addr_next = base_addr + operand_2_in[4:0];
            	            //store_din_r = operand_1_in;
            	            //store_en_next = 1'b1;
            	        end
            	    end
            	end
				// 
				// load_addr_next = operand_2_in[4:0] + base_addr;
				alu_state_next = EMPTY2_S;
			end
		end
        EMPTY2_S: begin
            //wait for the result of RAM
			if (ready_in) begin
				alu_state_next = IDLE_S;
				container_out_valid_next = 1;
				ready_out_next = 1;

				// action_type
				if ((action_type==4'b1000 || action_type==4'b0111) &&
						overflow==0) begin
					store_en_next = 1'b1;
				end
			end
			else begin
				alu_state_next = HALT_S;
			end
        end
		HALT_S: begin
			if (ready_in) begin
				alu_state_next = IDLE_S;
				container_out_valid_next = 1;
				ready_out_next = 1;

				// action_type
				if ((action_type==4'b1000 || action_type==4'b0111) &&
						overflow==0) begin
					store_en_next = 1'b1;
				end
			end
		end
	endcase
end

always @(posedge clk) begin
	if (~rst_n) begin
		alu_state <= IDLE_S;

		action_type <= 0;
		container_out <= 0;
		container_out_valid <= 0;

		store_en <= 0;
		store_addr <= 0;
		store_din <= 0;
		// load_addr <= 0;

        overflow <= 0;

		ready_out <= 1'b1;

	end
	else begin
		alu_state <= alu_state_next;
		action_type <= action_type_next;
		container_out <= container_out_next;
		container_out_valid <= container_out_valid_next;

		store_en <= store_en_next;
		store_addr <= store_addr_next;
		store_din <= store_din_next;
		// load_addr <= load_addr_next;

        overflow <= overflow_next;

		ready_out <= ready_out_next;

	end
end



blk_mem_gen_0
data_ram_32w_32d
(
    //store-related
    .addra(store_addr),
    .clka(clk),
    .dina(store_din_w),
    .ena(1'b1),
    .wea(store_en),

    //load-related
    .addrb(load_addr),
    .clkb(clk),
    .doutb(load_data),
    .enb(1'b1)
);


endmodule
