`timescale 1ns / 1ps
module action_engine #(
    parameter STAGE_ID = 0,
    parameter PHV_LEN = 48*8+32*8+16*8+256,
    parameter ACT_LEN = 25,
    parameter ACTION_ID = 3,
    parameter C_S_AXIS_DATA_WIDTH = 512,
    parameter C_S_AXIS_TUSER_WIDTH = 128,
	parameter C_VLANID_WIDTH = 12
)(
    input clk,
    input rst_n,

    //signals from lookup to ALUs
    input [PHV_LEN-1:0]           phv_in,
    input                         phv_valid_in,
    input [ACT_LEN*25-1:0]        action_in,
    input                         action_valid_in,
    output                        ready_out,

    //signals output from ALUs
    output reg [PHV_LEN-1:0]      phv_out,
    output reg                    phv_valid_out,
    input                         ready_in,
	// vlan input from lookup module
	input [C_VLANID_WIDTH-1:0]			act_vlan_in,
	input								act_vlan_valid_in,
	output reg							act_vlan_ready,
	// vlan
	// output reg [C_VLANID_WIDTH-1:0]		vlan_out_d1,
	// output reg							vlan_out_valid_d1,
	output reg [C_VLANID_WIDTH-1:0]		vlan_out,
	output reg							vlan_out_valid,
	input								vlan_out_ready,

    //control path
    input [C_S_AXIS_DATA_WIDTH-1:0]				c_s_axis_tdata,
	input [C_S_AXIS_TUSER_WIDTH-1:0]			c_s_axis_tuser,
	input [C_S_AXIS_DATA_WIDTH/8-1:0]			c_s_axis_tkeep,
	input										c_s_axis_tvalid,
	input										c_s_axis_tlast,

    output reg [C_S_AXIS_DATA_WIDTH-1:0]		c_m_axis_tdata,
	output reg [C_S_AXIS_TUSER_WIDTH-1:0]		c_m_axis_tuser,
	output reg [C_S_AXIS_DATA_WIDTH/8-1:0]		c_m_axis_tkeep,
	output reg 								    c_m_axis_tvalid,
	output reg 								    c_m_axis_tlast
);

                        
/********intermediate variables declared here********/
localparam width_2B = 16;
localparam width_4B = 32;
localparam width_6B = 48;

wire                        alu_in_valid;
wire [width_6B*8-1:0]       alu_in_6B_1;
wire [width_6B*8-1:0]       alu_in_6B_2;
wire [width_4B*8-1:0]       alu_in_4B_1;
wire [width_4B*8-1:0]       alu_in_4B_2;
wire [width_4B*8-1:0]       alu_in_4B_3;
wire [width_2B*8-1:0]       alu_in_2B_1;
wire [width_2B*8-1:0]       alu_in_2B_2;
wire [255:0]                alu_in_phv_remain_data;
wire [ACT_LEN*25-1:0]       alu_in_action;
wire                        alu_in_action_valid;

// reg                        alu_in_valid_d1;
// reg [width_6B*8-1:0]       alu_in_6B_1_d1;
// reg [width_6B*8-1:0]       alu_in_6B_2_d1;
// reg [width_4B*8-1:0]       alu_in_4B_1_d1;
// reg [width_4B*8-1:0]       alu_in_4B_2_d1;
// reg [width_4B*8-1:0]       alu_in_4B_3_d1;
// reg [width_2B*8-1:0]       alu_in_2B_1_d1;
// reg [width_2B*8-1:0]       alu_in_2B_2_d1;
// reg [255:0]                alu_in_phv_remain_data_d1;
// reg [ACT_LEN*25-1:0]       alu_in_action_d1;
// reg                        alu_in_action_valid_d1;


// output phv
wire		                phv_valid_bit;

//
wire                        alu_ready_out;
reg							act_vlan_ready_next;

reg							page_tbl_out_valid, page_tbl_out_valid_next;
// reg							page_tbl_out_valid_d1;
// output from ram
wire [15:0]					page_tbl_out;
// reg [15:0]					page_tbl_out_d1;

/********intermediate variables declared here********/
/********IPs instancilized here*********/

wire [width_6B-1:0]			output_6B[0:7];
wire [width_4B-1:0]			output_4B[0:7];
wire [width_2B-1:0]			output_2B[0:7];
wire [255:0]				output_md;


reg [PHV_LEN-1:0]	phv_out_r;
reg					phv_valid_out_r;

always @(*) begin

	phv_out_r = phv_out;
	phv_valid_out_r = 0;

	if (phv_valid_bit) begin
		phv_valid_out_r = 1;
		phv_out_r = {output_6B[7], output_6B[6], output_6B[5], output_6B[4], output_6B[3], output_6B[2], output_6B[1], output_6B[0],
				output_4B[7], output_4B[6], output_4B[5], output_4B[4], output_4B[3], output_4B[2], output_4B[1], output_4B[0],
				output_2B[7], output_2B[6], output_2B[5], output_2B[4], output_2B[3], output_2B[2], output_2B[1], output_2B[0], output_md};
	end
end

always @(posedge clk) begin
	if (~rst_n) begin
		phv_out <= 0;
		phv_valid_out <= 0;
	end
	else begin
		phv_out <= phv_out_r;
		phv_valid_out <= phv_valid_out_r;
	end
end

//================================================================
// vlan out logic
localparam		IDLE=0,
				EMPTY_1=1,
				FLUSH_VLAN=2;

reg [C_VLANID_WIDTH-1:0]	vlan_out_next;
reg							vlan_out_valid_next;
reg	[1:0]					state, state_next;


always @(*) begin

	state_next = state;
	vlan_out_next = vlan_out;
	vlan_out_valid_next = 0;

	case (state)
		IDLE: begin
			if (phv_valid_in) begin
				vlan_out_next = phv_in[140:129];

				state_next = FLUSH_VLAN;
			end
		end
		FLUSH_VLAN: begin
			if (vlan_out_ready) begin
				vlan_out_valid_next = 1;
				state_next = IDLE;
			end
		end
	endcase
end

always @(posedge clk) begin
	if (~rst_n) begin
		state <= IDLE;
		vlan_out <= 0;
		vlan_out_valid <= 0;

		//vlan_out_d1 <= 0;
		//vlan_out_valid_d1 <= 0;
	end
	else begin
		state <= state_next;
		vlan_out <= vlan_out_next;
		vlan_out_valid <= vlan_out_valid_next;

		// vlan_out_d1 <= vlan_out;
		// vlan_out_valid_d1 <= vlan_out_valid;
	end
end

localparam	VLAN_FIFO_IDLE=0,
			VLAN_FIFO_1CYCLE=1;

reg [2:0] vlan_fifo_state, vlan_fifo_state_next;

always @(*) begin
	vlan_fifo_state_next = vlan_fifo_state;
	act_vlan_ready_next = act_vlan_ready;
	page_tbl_out_valid_next = 0;

	case (vlan_fifo_state) 
		VLAN_FIFO_IDLE: begin
			if (act_vlan_valid_in) begin
				vlan_fifo_state_next = VLAN_FIFO_1CYCLE;
				act_vlan_ready_next = 0;
			end
		end
		VLAN_FIFO_1CYCLE: begin
			vlan_fifo_state_next = VLAN_FIFO_IDLE;
			act_vlan_ready_next = 1;
			page_tbl_out_valid_next = 1;
		end
	endcase
end

always @(posedge clk) begin
	if (~rst_n) begin
		vlan_fifo_state <= VLAN_FIFO_IDLE;
		act_vlan_ready <= 1;
		page_tbl_out_valid <= 0;
	end
	else begin
		vlan_fifo_state <= vlan_fifo_state_next;
		act_vlan_ready <= act_vlan_ready_next;
		page_tbl_out_valid <= page_tbl_out_valid_next;
	end
end


// delay 1 cycle
// always @(posedge clk) begin
// 	if (~rst_n) begin
// 		alu_in_valid_d1				<= 0;
// 		alu_in_6B_1_d1				<= 0;
// 		alu_in_6B_2_d1				<= 0;
// 		alu_in_4B_1_d1				<= 0;
// 		alu_in_4B_2_d1				<= 0;
// 		alu_in_4B_3_d1				<= 0;
// 		alu_in_2B_1_d1				<= 0;
// 		alu_in_2B_2_d1				<= 0;
// 		alu_in_phv_remain_data_d1	<= 0;
// 		alu_in_action_d1			<= 0;
// 		alu_in_action_valid_d1		<= 0;
// 		page_tbl_out_valid_d1		<= 0;
// 		page_tbl_out_d1				<= 0;
// 	end
// 	else begin
// 		alu_in_valid_d1				<=	alu_in_valid;
// 		alu_in_6B_1_d1				<=	alu_in_6B_1;
// 		alu_in_6B_2_d1				<=	alu_in_6B_2;
// 		alu_in_4B_1_d1				<=	alu_in_4B_1;
// 		alu_in_4B_2_d1				<=	alu_in_4B_2;
// 		alu_in_4B_3_d1				<=	alu_in_4B_3;
// 		alu_in_2B_1_d1				<=	alu_in_2B_1;
// 		alu_in_2B_2_d1				<=	alu_in_2B_2;
// 		alu_in_phv_remain_data_d1	<=	alu_in_phv_remain_data;
// 		alu_in_action_d1			<=	alu_in_action;
// 		alu_in_action_valid_d1		<=	alu_in_action_valid;
// 		page_tbl_out_valid_d1		<=	page_tbl_out_valid;
// 		page_tbl_out_d1				<=	page_tbl_out;
// 	end
// end

//crossbar
crossbar #(
    .STAGE_ID(STAGE_ID),
    .PHV_LEN(),
    .ACT_LEN(),
    .width_2B(),
    .width_4B(),
    .width_6B()
)cross_bar(
    .clk(clk),
    .rst_n(rst_n),
    //input from PHV
    .phv_in(phv_in),
    .phv_in_valid(phv_valid_in),
    //input from action
    .action_in(action_in),
    .action_in_valid(action_valid_in),
    .ready_out(ready_out),
    //output to the ALU
    .alu_in_valid(alu_in_valid),
    .alu_in_6B_1(alu_in_6B_1),
    .alu_in_6B_2(alu_in_6B_2),
    .alu_in_4B_1(alu_in_4B_1),
    .alu_in_4B_2(alu_in_4B_2),
    .alu_in_4B_3(alu_in_4B_3),
    .alu_in_2B_1(alu_in_2B_1),
    .alu_in_2B_2(alu_in_2B_2),
    .phv_remain_data(alu_in_phv_remain_data),
    .action_out(alu_in_action),
    .action_valid_out(alu_in_action_valid),
    .ready_in(alu_ready_out)
);



//ALU_1
genvar gen_i;
generate
    //initialize 8 6B containers 
    for(gen_i = 7; gen_i >= 0; gen_i = gen_i - 1) begin
        alu_1 #(
            .STAGE_ID(STAGE_ID),
            .ACTION_LEN(),
            .DATA_WIDTH(width_6B)
        )alu_1_6B(
            .clk(clk),
            .rst_n(rst_n),
            .action_in(alu_in_action[(gen_i+8+8+1+1)*ACT_LEN-1 -: ACT_LEN]),
            .action_valid(alu_in_action_valid),
            .operand_1_in(alu_in_6B_1[(gen_i+1) * width_6B -1 -: width_6B]),
            .operand_2_in(alu_in_6B_2[(gen_i+1) * width_6B -1 -: width_6B]),
            // .container_out(phv_out[width_4B*8+width_2B*8+356+width_6B*(gen_i+1)-1 -: width_6B]),
            .container_out(output_6B[gen_i]),
            .container_out_valid()
        );

        alu_1 #(
            .STAGE_ID(STAGE_ID),
            .ACTION_LEN(),
            .DATA_WIDTH(width_2B)
        )alu_1_2B(
            .clk(clk),
            .rst_n(rst_n),
            .action_in(alu_in_action[(gen_i+1+1)*ACT_LEN-1 -: ACT_LEN]),
            .action_valid(alu_in_action_valid),
            .operand_1_in(alu_in_2B_1[(gen_i+1) * width_2B -1 -: width_2B]),
            .operand_2_in(alu_in_2B_2[(gen_i+1) * width_2B -1 -: width_2B]),
            // .container_out(phv_out[356+width_2B*(gen_i+1) -1 -: width_2B]),
            .container_out(output_2B[gen_i]),
            .container_out_valid()
        );
	end
endgenerate

alu_2 #(
    .STAGE_ID(STAGE_ID),
    .ACTION_LEN(),
    .DATA_WIDTH(width_4B),  //data width of the ALU
    .C_S_AXIS_DATA_WIDTH(C_S_AXIS_DATA_WIDTH),
    .C_S_AXIS_TUSER_WIDTH(C_S_AXIS_TUSER_WIDTH)
)alu_2_0(
    .clk(clk),
    .rst_n(rst_n),
    //input from sub_action
    .action_in(alu_in_action[(7+8+1+1)*ACT_LEN-1 -: ACT_LEN]),
    .action_valid(alu_in_action_valid),
    .operand_1_in(alu_in_4B_1[(7+1) * width_4B -1 -: width_4B]),
    .operand_2_in(alu_in_4B_2[(7+1) * width_4B -1 -: width_4B]),
    .operand_3_in(alu_in_4B_3[(7+1) * width_4B -1 -: width_4B]),
    .ready_out(alu_ready_out),
	//
	.page_tbl_out			(page_tbl_out),
	.page_tbl_out_valid		(page_tbl_out_valid),
    //output to form PHV
    .container_out_w(output_4B[7]),
    .container_out_valid(),
    .ready_in(ready_in)
);

generate
    for(gen_i = 6; gen_i >= 0; gen_i = gen_i - 1) begin
		alu_1 #(
		    .STAGE_ID(STAGE_ID),
		    .ACTION_LEN(),
		    .DATA_WIDTH(width_4B)
		)alu_1_4B(
		    .clk(clk),
		    .rst_n(rst_n),
		    .action_in(alu_in_action[(gen_i+8+1+1)*ACT_LEN-1 -: ACT_LEN]),
		    .action_valid(alu_in_action_valid),
		    .operand_1_in(alu_in_4B_1[(gen_i+1) * width_4B -1 -: width_4B]),
		    .operand_2_in(alu_in_4B_2[(gen_i+1) * width_4B -1 -: width_4B]),
		    // .container_out(phv_out[width_2B*8+356+width_4B*(gen_i+1) -1 -: width_4B]),
		    .container_out(output_4B[gen_i]),
		    .container_out_valid()
		);
    end
endgenerate


//initialize ALU_3 for matedata

alu_3 #(
    .STAGE_ID(STAGE_ID),
    .ACTION_LEN(),
    .META_LEN()
)alu_3_0(
    .clk(clk),
    .rst_n(rst_n),
    //input data shall be metadata & com_ins
    .comp_meta_data_in(alu_in_phv_remain_data),
    .comp_meta_data_valid_in(alu_in_valid),
    .action_in(alu_in_action[24:0]),
    .action_valid_in(alu_in_action_valid),

    //output is the modified metadata plus comp_ins
    // .comp_meta_data_out(phv_out[355:0]),
    .comp_meta_data_out(output_md),
    .comp_meta_data_valid_out(phv_valid_bit)
);




/*
    CONTROL PATH
*/

generate 
	if (C_S_AXIS_DATA_WIDTH == 512) begin
		/****control path for 512b*****/
		wire [7:0]          mod_id; //module ID
		wire [15:0]         control_flag; //dst udp port num
		reg  [7:0]          c_index; //table index(addr)
		reg                 c_wr_en; //enable table write(wen)
		reg [15:0]			entry_reg;
		
		reg  [2:0]          c_state;
		
		localparam IDLE_C = 0,
		           WRITE_C = 1,
				   SU_WRITE_C = 2;
		
		assign mod_id = c_s_axis_tdata[368+:8];
		assign control_flag = c_s_axis_tdata[335:320];
		
		//LE to BE switching
		wire[C_S_AXIS_DATA_WIDTH-1:0] c_s_axis_tdata_swapped;
		assign c_s_axis_tdata_swapped = {	c_s_axis_tdata[0+:8],
											c_s_axis_tdata[8+:8],
											c_s_axis_tdata[16+:8],
											c_s_axis_tdata[24+:8],
											c_s_axis_tdata[32+:8],
											c_s_axis_tdata[40+:8],
											c_s_axis_tdata[48+:8],
											c_s_axis_tdata[56+:8],
											c_s_axis_tdata[64+:8],
											c_s_axis_tdata[72+:8],
											c_s_axis_tdata[80+:8],
											c_s_axis_tdata[88+:8],
											c_s_axis_tdata[96+:8],
											c_s_axis_tdata[104+:8],
											c_s_axis_tdata[112+:8],
											c_s_axis_tdata[120+:8],
											c_s_axis_tdata[128+:8],
											c_s_axis_tdata[136+:8],
											c_s_axis_tdata[144+:8],
											c_s_axis_tdata[152+:8],
											c_s_axis_tdata[160+:8],
											c_s_axis_tdata[168+:8],
											c_s_axis_tdata[176+:8],
											c_s_axis_tdata[184+:8],
											c_s_axis_tdata[192+:8],
											c_s_axis_tdata[200+:8],
											c_s_axis_tdata[208+:8],
											c_s_axis_tdata[216+:8],
											c_s_axis_tdata[224+:8],
											c_s_axis_tdata[232+:8],
											c_s_axis_tdata[240+:8],
											c_s_axis_tdata[248+:8],
		                                    c_s_axis_tdata[256+:8],
		                                    c_s_axis_tdata[264+:8],
		                                    c_s_axis_tdata[272+:8],
		                                    c_s_axis_tdata[280+:8],
		                                    c_s_axis_tdata[288+:8],
		                                    c_s_axis_tdata[296+:8],
		                                    c_s_axis_tdata[304+:8],
		                                    c_s_axis_tdata[312+:8],
		                                    c_s_axis_tdata[320+:8],
		                                    c_s_axis_tdata[328+:8],
		                                    c_s_axis_tdata[336+:8],
		                                    c_s_axis_tdata[344+:8],
		                                    c_s_axis_tdata[352+:8],
		                                    c_s_axis_tdata[360+:8],
		                                    c_s_axis_tdata[368+:8],
		                                    c_s_axis_tdata[376+:8],
		                                    c_s_axis_tdata[384+:8],
		                                    c_s_axis_tdata[392+:8],
		                                    c_s_axis_tdata[400+:8],
		                                    c_s_axis_tdata[408+:8],
		                                    c_s_axis_tdata[416+:8],
		                                    c_s_axis_tdata[424+:8],
		                                    c_s_axis_tdata[432+:8],
		                                    c_s_axis_tdata[440+:8],
		                                    c_s_axis_tdata[448+:8],
		                                    c_s_axis_tdata[456+:8],
		                                    c_s_axis_tdata[464+:8],
		                                    c_s_axis_tdata[472+:8],
		                                    c_s_axis_tdata[480+:8],
		                                    c_s_axis_tdata[488+:8],
		                                    c_s_axis_tdata[496+:8],
		                                    c_s_axis_tdata[504+:8]
		                                };
		
		always @(posedge clk or negedge rst_n) begin
		    if(~rst_n) begin
		        c_wr_en <= 1'b0;
		        c_index <= 4'b0;
		
		        c_m_axis_tdata <= 0;
		        c_m_axis_tuser <= 0;
		        c_m_axis_tkeep <= 0;
		        c_m_axis_tvalid <= 0;
		        c_m_axis_tlast <= 0;

				entry_reg <= 0;
		
		        c_state <= IDLE_C;
		    end
		    else begin
		        case(c_state)
		            IDLE_C: begin
		                if(c_s_axis_tvalid && mod_id[7:3] == STAGE_ID && mod_id[2:0] == ACTION_ID && control_flag == 16'hf2f1)begin
		                    c_wr_en <= 1'b0;
		                    c_index <= c_s_axis_tdata[384+:8];
		
		                    c_m_axis_tdata <= 0;
		                    c_m_axis_tuser <= 0;
		                    c_m_axis_tkeep <= 0;
		                    c_m_axis_tvalid <= 0;
		                    c_m_axis_tlast <= 0;
		
		                    c_state <= WRITE_C;
		
		                end
		                else begin
		                    c_wr_en <= 1'b0;
		                    c_index <= 4'b0; 
		
		                    c_m_axis_tdata <= c_s_axis_tdata;
		                    c_m_axis_tuser <= c_s_axis_tuser;
		                    c_m_axis_tkeep <= c_s_axis_tkeep;
		                    c_m_axis_tvalid <= c_s_axis_tvalid;
		                    c_m_axis_tlast <= c_s_axis_tlast;
		
		                    c_state <= IDLE_C;
		                end
		            end
		            //support full table flush
					WRITE_C: begin
						if(c_s_axis_tvalid) begin
							c_wr_en <= 1'b1;
							entry_reg <= c_s_axis_tdata_swapped[511 -: 16];
							if(c_s_axis_tlast) begin
								c_state <= IDLE_C;
							end
							else begin
								c_state <= SU_WRITE_C;
							end
						end
						else begin
							c_wr_en <= 1'b0;
						end
					end

					SU_WRITE_C: begin
						if(c_s_axis_tvalid) begin
							entry_reg <= c_s_axis_tdata_swapped[511 -: 16];
							c_wr_en <= 1'b1;
							c_index <= c_index + 1'b1;
							if(c_s_axis_tlast) begin
								c_state <= IDLE_C;
							end
							else begin
								c_state <= SU_WRITE_C;
							end
						end
						else begin
							c_wr_en <= 1'b0;
						end
					end
		        endcase
		
		    end
		end
		
		
		//page table
		page_tbl_16w_32d
		page_tbl_16w_32d
		(
		    //write
		    .addra(c_index[4:0]),
		    .clka(clk),
		    .dina(entry_reg),
		    .ena(1'b1),
		    .wea(c_wr_en),
		
		    //match
		    .addrb(act_vlan_in[8:4]),
		    .clkb(clk),
		    .doutb(page_tbl_out),
		    .enb(1'b1)
		);
	end
	else begin // control path for 256b
		wire [7:0]          mod_id; //module ID
		wire [15:0]         control_flag; //dst udp port num
		wire[C_S_AXIS_DATA_WIDTH-1:0] c_s_axis_tdata_swapped;
		assign c_s_axis_tdata_swapped = {	c_s_axis_tdata[0+:8],
											c_s_axis_tdata[8+:8],
											c_s_axis_tdata[16+:8],
											c_s_axis_tdata[24+:8],
											c_s_axis_tdata[32+:8],
											c_s_axis_tdata[40+:8],
											c_s_axis_tdata[48+:8],
											c_s_axis_tdata[56+:8],
											c_s_axis_tdata[64+:8],
											c_s_axis_tdata[72+:8],
											c_s_axis_tdata[80+:8],
											c_s_axis_tdata[88+:8],
											c_s_axis_tdata[96+:8],
											c_s_axis_tdata[104+:8],
											c_s_axis_tdata[112+:8],
											c_s_axis_tdata[120+:8],
											c_s_axis_tdata[128+:8],
											c_s_axis_tdata[136+:8],
											c_s_axis_tdata[144+:8],
											c_s_axis_tdata[152+:8],
											c_s_axis_tdata[160+:8],
											c_s_axis_tdata[168+:8],
											c_s_axis_tdata[176+:8],
											c_s_axis_tdata[184+:8],
											c_s_axis_tdata[192+:8],
											c_s_axis_tdata[200+:8],
											c_s_axis_tdata[208+:8],
											c_s_axis_tdata[216+:8],
											c_s_axis_tdata[224+:8],
											c_s_axis_tdata[232+:8],
											c_s_axis_tdata[240+:8],
											c_s_axis_tdata[248+:8]};

        assign mod_id = c_s_axis_tdata[112+:8];
        assign control_flag = c_s_axis_tdata[64+:16];
		localparam	IDLE_C = 0,
					PARSE_C = 1,
					RAM_ENTRY = 2,
					FLUSH_REST_C = 3;
		// 
		reg [2:0] c_state, c_state_next;
		reg [C_S_AXIS_DATA_WIDTH-1:0]		r_tdata, c_s_axis_tdata_d1;
		reg [C_S_AXIS_TUSER_WIDTH-1:0]		r_tuser, c_s_axis_tuser_d1;
		reg [C_S_AXIS_DATA_WIDTH/8-1:0]		r_tkeep, c_s_axis_tkeep_d1;
		reg									r_tlast, c_s_axis_tlast_d1;
		reg									r_tvalid, c_s_axis_tvalid_d1;

		reg [C_S_AXIS_DATA_WIDTH-1:0]		r_1st_tdata, r_1st_tdata_next;
		reg [C_S_AXIS_TUSER_WIDTH-1:0]		r_1st_tuser, r_1st_tuser_next;
		reg [C_S_AXIS_DATA_WIDTH/8-1:0]		r_1st_tkeep, r_1st_tkeep_next;
		reg									r_1st_tlast, r_1st_tlast_next;
		reg									r_1st_tvalid, r_1st_tvalid_next;

		reg [15:0]							c_wr_data_next, c_wr_data;
		reg [7:0]							c_index_next, c_index;
		reg									c_wr_en_next, c_wr_en;

		always @(*) begin
			c_state_next = c_state;

			r_tdata = 0;
			r_tkeep = 0;
			r_tuser = 0;
			r_tlast = 0;
			r_tvalid = 0;

			r_1st_tdata_next = r_1st_tdata;
			r_1st_tkeep_next = r_1st_tkeep;
			r_1st_tuser_next = r_1st_tuser;
			r_1st_tlast_next = r_1st_tlast;
			r_1st_tvalid_next = r_1st_tvalid;

			c_index_next = c_index;
			c_wr_en_next = 0;
			c_wr_data_next = c_wr_data;

			case (c_state) 
				IDLE_C: begin // 1st segment
					r_tvalid = 0;
					if (c_s_axis_tvalid) begin
						// store 1st segment
						r_1st_tdata_next = c_s_axis_tdata;
						r_1st_tuser_next = c_s_axis_tuser;
						r_1st_tkeep_next = c_s_axis_tkeep;
						r_1st_tlast_next = c_s_axis_tlast;
						r_1st_tvalid_next = c_s_axis_tvalid;

						c_state_next = PARSE_C;
					end
				end
				PARSE_C: begin // 2nd segment
					if (mod_id[7:3] == STAGE_ID && mod_id[2:0] == ACTION_ID && 
						control_flag == 16'hf2f1 && c_s_axis_tvalid) begin
						// should not emit segment
						c_index_next = c_s_axis_tdata[128+:8];
						c_state_next = RAM_ENTRY;
					end
					else if (!c_s_axis_tvalid) begin
					end
					else begin
						// emit
						r_tdata = r_1st_tdata;
						r_tkeep = r_1st_tkeep;
						r_tuser = r_1st_tuser;
						r_tlast = r_1st_tlast;
						r_tvalid = r_1st_tvalid;
						c_state_next = FLUSH_REST_C;
					end
				end
				RAM_ENTRY: begin // 3rd segment
					if (c_s_axis_tvalid) begin
						c_wr_en_next = 1; // next clk to write
						c_wr_data_next = c_s_axis_tdata_swapped[255-:16];
						
						c_state_next = FLUSH_REST_C;
					end
				end
				FLUSH_REST_C: begin
					c_wr_en_next = 0;
					r_tdata = c_s_axis_tdata_d1;
					r_tkeep = c_s_axis_tkeep_d1;
					r_tuser = c_s_axis_tuser_d1;
					r_tlast = c_s_axis_tlast_d1;
					r_tvalid = c_s_axis_tvalid_d1;
					if (c_s_axis_tvalid_d1 && c_s_axis_tlast_d1) begin
						c_state_next = IDLE_C;
					end
				end
			endcase
		end

		always @(posedge clk) begin
			if (~rst_n) begin
				c_state <= IDLE_C;

				// control output
				c_m_axis_tdata <= 0;
				c_m_axis_tuser <= 0;
				c_m_axis_tkeep <= 0;
				c_m_axis_tlast <= 0;
				c_m_axis_tvalid <= 0;
				//
				c_index <= 0;
				c_wr_en <= 0;
				c_wr_data <= 0;
			end
			else begin
				c_state <= c_state_next;


				// output ctrl master signals
				c_m_axis_tdata <= r_tdata;
				c_m_axis_tkeep <= r_tkeep;
				c_m_axis_tuser <= r_tuser;
				c_m_axis_tlast <= r_tlast;
				c_m_axis_tvalid <= r_tvalid;
				//
				c_index <= c_index_next;
				c_wr_en <= c_wr_en_next;
				c_wr_data <= c_wr_data_next;
			end
		end

		always @(posedge clk) begin
			if (~rst_n) begin
				// delayed 1 clk
				c_s_axis_tdata_d1 <= 0;
				c_s_axis_tuser_d1 <= 0;
				c_s_axis_tkeep_d1 <= 0;
				c_s_axis_tlast_d1 <= 0;
				c_s_axis_tvalid_d1 <= 0;
				//
				r_1st_tdata <= 0;
				r_1st_tkeep <= 0;
				r_1st_tuser <= 0;
				r_1st_tlast <= 0;
				r_1st_tvalid <= 0;
			end
			else begin
				// delayed 1 clk
				c_s_axis_tdata_d1 <= c_s_axis_tdata;
				c_s_axis_tuser_d1 <= c_s_axis_tuser;
				c_s_axis_tkeep_d1 <= c_s_axis_tkeep;
				c_s_axis_tlast_d1 <= c_s_axis_tlast;
				c_s_axis_tvalid_d1 <= c_s_axis_tvalid;
				// 
				r_1st_tdata <= r_1st_tdata_next;
				r_1st_tkeep <= r_1st_tkeep_next;
				r_1st_tuser <= r_1st_tuser_next;
				r_1st_tlast <= r_1st_tlast_next;
				r_1st_tvalid <= r_1st_tvalid_next;
			end
		end
		//page table
		page_tbl_16w_32d
		page_tbl_16w_32d
		(
		    //write
		    .addra(c_index[4:0]),
		    .clka(clk),
		    .dina(c_wr_data),
		    .ena(1'b1),
		    .wea(c_wr_en),
		
		    //match
		    .addrb(act_vlan_in[8:4]),
		    .clkb(clk),
		    .doutb(page_tbl_out),
		    .enb(1'b1)
		);
	end
endgenerate



endmodule
