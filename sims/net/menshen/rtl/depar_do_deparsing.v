`timescale 1ns / 1ps

`define SUB_DEPARSE_1P(idx) \
	if(parse_action[idx][0]) begin \
		case(sub_depar_val_out_type_d1[idx]) \
			2'b01: pkts_tdata_stored_1p_next[parse_action_ind_10b[idx]<<3 +: 16] = sub_depar_val_out_swapped[idx][32+:16]; \
			2'b10: pkts_tdata_stored_1p_next[parse_action_ind_10b[idx]<<3 +: 32] = sub_depar_val_out_swapped[idx][16+:32]; \
			2'b11: pkts_tdata_stored_1p_next[parse_action_ind_10b[idx]<<3 +: 48] = sub_depar_val_out_swapped[idx][0+:48]; \
		endcase \
	end \

`define SUB_DEPARSE_2P(idx) \
	if(parse_action[idx][0]) begin \
		case(sub_depar_val_out_type_d1[idx]) \
			2'b01: pkts_tdata_stored_2p_next[parse_action_ind_10b[idx]<<3 +: 16] = sub_depar_val_out_swapped[idx][32+:16]; \
			2'b10: pkts_tdata_stored_2p_next[parse_action_ind_10b[idx]<<3 +: 32] = sub_depar_val_out_swapped[idx][16+:32]; \
			2'b11: pkts_tdata_stored_2p_next[parse_action_ind_10b[idx]<<3 +: 48] = sub_depar_val_out_swapped[idx][0+:48]; \
		endcase \
	end \

`define SWAP_BYTE_ORDER2(idx) \
	assign sub_depar_val_out_swapped[idx] = {	sub_depar_val_out_d1[idx][0+:8], \
												sub_depar_val_out_d1[idx][8+:8], \
												sub_depar_val_out_d1[idx][16+:8], \
												sub_depar_val_out_d1[idx][24+:8], \
												sub_depar_val_out_d1[idx][32+:8], \
												sub_depar_val_out_d1[idx][40+:8]}; \

module depar_do_deparsing #(
	parameter	C_AXIS_DATA_WIDTH = 512,
	parameter	C_AXIS_TUSER_WIDTH = 128,
	parameter	C_PKT_VEC_WIDTH = (6+4+2)*8*8+256,
	parameter	DEPARSER_MOD_ID = 3'b101,
	parameter	C_VLANID_WIDTH = 12
)
(
	input													clk,
	input													aresetn,

	// phv
	input [C_PKT_VEC_WIDTH-1:0]								phv_fifo_out,
	input													phv_fifo_empty,
	output reg												phv_fifo_rd_en,

	//
	input [C_VLANID_WIDTH-1:0]								vlan_id,
	input													vlan_fifo_empty,
	output reg												vlan_fifo_rd_en,
	// 
	input [C_AXIS_DATA_WIDTH-1:0]							fst_half_fifo_tdata,
	input [C_AXIS_TUSER_WIDTH-1:0]							fst_half_fifo_tuser,
	input [C_AXIS_DATA_WIDTH/8-1:0]							fst_half_fifo_tkeep,
	input													fst_half_fifo_tlast,
	input													fst_half_fifo_empty,
	output reg												fst_half_fifo_rd_en,
	// 
	input [C_AXIS_DATA_WIDTH-1:0]							snd_half_fifo_tdata,
	input [C_AXIS_TUSER_WIDTH-1:0]							snd_half_fifo_tuser,
	input [C_AXIS_DATA_WIDTH/8-1:0]							snd_half_fifo_tkeep,
	input													snd_half_fifo_tlast,
	input													snd_half_fifo_empty,
	output reg												snd_half_fifo_rd_en,
	//
	input [C_AXIS_DATA_WIDTH-1:0]							pkt_fifo_tdata,
	input [C_AXIS_TUSER_WIDTH-1:0]							pkt_fifo_tuser,
	input [C_AXIS_DATA_WIDTH/8-1:0]							pkt_fifo_tkeep,
	input													pkt_fifo_tlast,
	input													pkt_fifo_empty,
	output reg												pkt_fifo_rd_en,

	// output
	output reg [C_AXIS_DATA_WIDTH-1:0]						depar_out_tdata,
	output reg [C_AXIS_DATA_WIDTH/8-1:0]					depar_out_tkeep,
	output reg [C_AXIS_TUSER_WIDTH-1:0]						depar_out_tuser,
	output reg												depar_out_tvalid,
	output reg												depar_out_tlast,
	input													depar_out_tready,

	// control path
	input [C_AXIS_DATA_WIDTH-1:0]							ctrl_s_axis_tdata,
	input [C_AXIS_TUSER_WIDTH-1:0]							ctrl_s_axis_tuser,
	input [C_AXIS_DATA_WIDTH/8-1:0]							ctrl_s_axis_tkeep,
	input													ctrl_s_axis_tvalid,
	input													ctrl_s_axis_tlast
);

integer i;

reg [C_AXIS_DATA_WIDTH-1:0]						depar_out_tdata_next;
reg [C_AXIS_DATA_WIDTH/8-1:0]					depar_out_tkeep_next;
reg [C_AXIS_TUSER_WIDTH-1:0]					depar_out_tuser_next;
reg												depar_out_tlast_next;
reg												depar_out_tvalid_next;

wire [159:0] bram_out;
wire [6:0] parse_action_ind [0:9];
wire [9:0] parse_action_ind_10b [0:9];


wire [15:0] parse_action [0:9];		// we have 10 parse action
assign parse_action[9] = bram_out[0+:16];
assign parse_action[8] = bram_out[16+:16];
assign parse_action[7] = bram_out[32+:16];
assign parse_action[6] = bram_out[48+:16];
assign parse_action[5] = bram_out[64+:16];
assign parse_action[4] = bram_out[80+:16];
assign parse_action[3] = bram_out[96+:16];
assign parse_action[2] = bram_out[112+:16];
assign parse_action[1] = bram_out[128+:16];
assign parse_action[0] = bram_out[144+:16];

assign parse_action_ind[0] = parse_action[0][12:6];
assign parse_action_ind[1] = parse_action[1][12:6];
assign parse_action_ind[2] = parse_action[2][12:6];
assign parse_action_ind[3] = parse_action[3][12:6];
assign parse_action_ind[4] = parse_action[4][12:6];
assign parse_action_ind[5] = parse_action[5][12:6];
assign parse_action_ind[6] = parse_action[6][12:6];
assign parse_action_ind[7] = parse_action[7][12:6];
assign parse_action_ind[8] = parse_action[8][12:6];
assign parse_action_ind[9] = parse_action[9][12:6];

assign parse_action_ind_10b[0] = parse_action_ind[0];
assign parse_action_ind_10b[1] = parse_action_ind[1];
assign parse_action_ind_10b[2] = parse_action_ind[2];
assign parse_action_ind_10b[3] = parse_action_ind[3];
assign parse_action_ind_10b[4] = parse_action_ind[4];
assign parse_action_ind_10b[5] = parse_action_ind[5];
assign parse_action_ind_10b[6] = parse_action_ind[6];
assign parse_action_ind_10b[7] = parse_action_ind[7];
assign parse_action_ind_10b[8] = parse_action_ind[8];
assign parse_action_ind_10b[9] = parse_action_ind[9];


reg	[9:0]					sub_depar_act_valid;

wire [47:0]					sub_depar_val_out_swapped [0:9];
wire [47:0]					sub_depar_val_out [0:9];
wire [1:0]					sub_depar_val_out_type [0:9];
wire [9:0]					sub_depar_val_out_valid;


reg [47:0]					sub_depar_val_out_d1 [0:9];
reg [1:0]					sub_depar_val_out_type_d1 [0:9];
reg [9:0]					sub_depar_val_out_valid_d1;

always @(posedge clk) begin
	if (~aresetn) begin
		for (i=0; i<10; i=i+1) begin
			sub_depar_val_out_d1[i] <= 0;
			sub_depar_val_out_type_d1[i] <= 0;
		end
		sub_depar_val_out_valid_d1 <= 0;
	end
	else begin
		for (i=0; i<10; i=i+1) begin
			sub_depar_val_out_d1[i] <= sub_depar_val_out[i];
			sub_depar_val_out_type_d1[i] <= sub_depar_val_out_type[i];
		end
		sub_depar_val_out_valid_d1 <= sub_depar_val_out_valid;
	end
end

`SWAP_BYTE_ORDER2(0)
`SWAP_BYTE_ORDER2(1)
`SWAP_BYTE_ORDER2(2)
`SWAP_BYTE_ORDER2(3)
`SWAP_BYTE_ORDER2(4)
`SWAP_BYTE_ORDER2(5)
`SWAP_BYTE_ORDER2(6)
`SWAP_BYTE_ORDER2(7)
`SWAP_BYTE_ORDER2(8)
`SWAP_BYTE_ORDER2(9)

wire discard_signal;
assign discard_signal = phv_fifo_out[128];

localparam		IDLE=0,
				WAIT_1CYCLE_RAM=1,
				START_SUB_DEPARSE=2,
				FINISH_SUB_DEPARSER_0=3,
				FINISH_SUB_DEPARSER_1=4,
				FINISH_SUB_DEPARSER_2=5,
				FLUSH_PKT_0=6,
				FLUSH_PKT_1=7,
				FLUSH_PKT_2=8,
				FLUSH_PKT_3=9,
				FLUSH_PKT=10,
				DROP_PKT=11,
				DROP_PKT_REMAINING=12,
				EMPTY_1=13,
				EMPTY_2=14;


reg [C_AXIS_DATA_WIDTH-1:0]			pkts_tdata_stored_1p, pkts_tdata_stored_2p;
reg [C_AXIS_TUSER_WIDTH-1:0]		pkts_tuser_stored_1p, pkts_tuser_stored_2p;
reg [(C_AXIS_DATA_WIDTH/8)-1:0]		pkts_tkeep_stored_1p, pkts_tkeep_stored_2p;
reg									pkts_tlast_stored_1p, pkts_tlast_stored_2p;
reg [C_AXIS_DATA_WIDTH-1:0]			pkts_tdata_stored_1p_next, pkts_tdata_stored_2p_next;
reg [C_AXIS_TUSER_WIDTH-1:0]		pkts_tuser_stored_1p_next, pkts_tuser_stored_2p_next;
reg [(C_AXIS_DATA_WIDTH/8)-1:0]		pkts_tkeep_stored_1p_next, pkts_tkeep_stored_2p_next;
reg									pkts_tlast_stored_1p_next, pkts_tlast_stored_2p_next;

reg [4:0] state, state_next;

always @(*) begin

	phv_fifo_rd_en = 0;
	vlan_fifo_rd_en = 0;
	fst_half_fifo_rd_en = 0;
	snd_half_fifo_rd_en = 0;
	pkt_fifo_rd_en = 0;
	// output
	depar_out_tdata_next = depar_out_tdata;
	depar_out_tuser_next = depar_out_tuser;
	depar_out_tkeep_next = depar_out_tkeep;
	depar_out_tlast_next = depar_out_tlast;
	depar_out_tvalid_next = 0;

	sub_depar_act_valid = 10'b0;

	state_next = state;
	//
	pkts_tdata_stored_1p_next = pkts_tdata_stored_1p;
	pkts_tuser_stored_1p_next = pkts_tuser_stored_1p;
	pkts_tkeep_stored_1p_next = pkts_tkeep_stored_1p;
	pkts_tlast_stored_1p_next = pkts_tlast_stored_1p;
	//
	pkts_tdata_stored_2p_next = pkts_tdata_stored_2p;
	pkts_tuser_stored_2p_next = pkts_tuser_stored_2p;
	pkts_tkeep_stored_2p_next = pkts_tkeep_stored_2p;
	pkts_tlast_stored_2p_next = pkts_tlast_stored_2p;

	case (state) 
		IDLE: begin
			if (!vlan_fifo_empty) begin
				state_next = WAIT_1CYCLE_RAM;
			end
		end
		WAIT_1CYCLE_RAM: begin
			state_next = START_SUB_DEPARSE;
		end
		START_SUB_DEPARSE: begin
			if (!fst_half_fifo_empty 
					&& !snd_half_fifo_empty 
					&& !phv_fifo_empty) begin

				if (discard_signal == 1) begin
					state_next = DROP_PKT;
					phv_fifo_rd_en = 1;
				end
				else begin
					sub_depar_act_valid = 10'b1111111111;

					state_next = EMPTY_2;
					pkts_tdata_stored_1p_next = fst_half_fifo_tdata;
					pkts_tuser_stored_1p_next = phv_fifo_out[0+:128];
					pkts_tkeep_stored_1p_next = fst_half_fifo_tkeep;
					pkts_tlast_stored_1p_next = fst_half_fifo_tlast;
					//
					pkts_tdata_stored_2p_next = snd_half_fifo_tdata;
					pkts_tuser_stored_2p_next = snd_half_fifo_tuser;
					pkts_tkeep_stored_2p_next = snd_half_fifo_tkeep;
					pkts_tlast_stored_2p_next = snd_half_fifo_tlast;
				end
			end
		end
		EMPTY_1: begin
			// sub_depar_act_valid = 10'b1111111111;
			state_next = EMPTY_2;
		end
		EMPTY_2: begin
			state_next = FINISH_SUB_DEPARSER_0;
		end
		FINISH_SUB_DEPARSER_0: begin
			`SUB_DEPARSE_1P(0)
			`SUB_DEPARSE_1P(1)
			`SUB_DEPARSE_2P(5)

			state_next = FINISH_SUB_DEPARSER_1;
		end
		FINISH_SUB_DEPARSER_1: begin
			`SUB_DEPARSE_1P(2)
			`SUB_DEPARSE_2P(6)
			`SUB_DEPARSE_2P(7)

			state_next = FINISH_SUB_DEPARSER_2;
		end
		FINISH_SUB_DEPARSER_2: begin
			`SUB_DEPARSE_1P(3)
			`SUB_DEPARSE_1P(4)
			`SUB_DEPARSE_2P(8)
			`SUB_DEPARSE_2P(9)

			state_next = FLUSH_PKT_0;
		end
		FLUSH_PKT_0: begin
			phv_fifo_rd_en = 1;
			vlan_fifo_rd_en = 1;
			fst_half_fifo_rd_en = 1;
			snd_half_fifo_rd_en = 1;

			depar_out_tdata_next = pkts_tdata_stored_1p;
			depar_out_tuser_next = pkts_tuser_stored_1p;
			depar_out_tkeep_next = pkts_tkeep_stored_1p;
			depar_out_tlast_next = pkts_tlast_stored_1p;

			if (depar_out_tready) begin
				depar_out_tvalid_next = 1;
				if (pkts_tlast_stored_1p) begin
					state_next = IDLE;
				end
				else begin
					state_next = FLUSH_PKT_1;
				end
			end
		end
		FLUSH_PKT_1: begin
			depar_out_tdata_next = pkts_tdata_stored_2p;
			depar_out_tuser_next = pkts_tuser_stored_2p;
			depar_out_tkeep_next = pkts_tkeep_stored_2p;
			depar_out_tlast_next = pkts_tlast_stored_2p;

			if (depar_out_tready) begin
				depar_out_tvalid_next = 1;
				if (pkts_tlast_stored_2p) begin
					state_next = IDLE;
				end
				else begin
					state_next = FLUSH_PKT;
				end
			end
		end
		FLUSH_PKT: begin
			if (!pkt_fifo_empty) begin
				depar_out_tdata_next = pkt_fifo_tdata;
				depar_out_tuser_next =  pkt_fifo_tuser;
				depar_out_tkeep_next =  pkt_fifo_tkeep;
				depar_out_tlast_next =  pkt_fifo_tlast;
				if (depar_out_tready) begin
					pkt_fifo_rd_en = 1;
					depar_out_tvalid_next = 1;
					if (pkt_fifo_tlast) begin
						state_next = IDLE;
					end
				end
			end
		end
		DROP_PKT: begin
			if (fst_half_fifo_tlast==1 
				|| snd_half_fifo_tlast==1) begin
				fst_half_fifo_rd_en = 1;
				snd_half_fifo_rd_en = 1;
				vlan_fifo_rd_en = 1;

				state_next = IDLE;
			end
			else begin
				fst_half_fifo_rd_en = 1;
				snd_half_fifo_rd_en = 1;
				vlan_fifo_rd_en = 1;

				state_next = DROP_PKT_REMAINING;
			end
		end
		DROP_PKT_REMAINING: begin
			pkt_fifo_rd_en = 1;
			if (pkt_fifo_tlast) begin
				state_next = IDLE;
			end
		end
	endcase
end

always @(posedge clk) begin
	if (~aresetn) begin
		state <= IDLE;
		//
		pkts_tdata_stored_1p <= 0;
		pkts_tuser_stored_1p <= 0;
		pkts_tkeep_stored_1p <= 0;
		pkts_tlast_stored_1p <= 0;
		//
		pkts_tdata_stored_2p <= 0;
		pkts_tuser_stored_2p <= 0;
		pkts_tkeep_stored_2p <= 0;
		pkts_tlast_stored_2p <= 0;
		//
		depar_out_tdata <= 0;
		depar_out_tkeep <= 0;
		depar_out_tuser <= 0;
		depar_out_tlast <= 0;
		depar_out_tvalid <= 0;
	end
	else begin
		state <= state_next;
		//
		pkts_tdata_stored_1p <= pkts_tdata_stored_1p_next;
		pkts_tuser_stored_1p <= pkts_tuser_stored_1p_next;
		pkts_tkeep_stored_1p <= pkts_tkeep_stored_1p_next;
		pkts_tlast_stored_1p <= pkts_tlast_stored_1p_next;
		//
		pkts_tdata_stored_2p <= pkts_tdata_stored_2p_next;
		pkts_tuser_stored_2p <= pkts_tuser_stored_2p_next;
		pkts_tkeep_stored_2p <= pkts_tkeep_stored_2p_next;
		pkts_tlast_stored_2p <= pkts_tlast_stored_2p_next;
		//
		depar_out_tdata <= depar_out_tdata_next;
		depar_out_tkeep <= depar_out_tkeep_next;
		depar_out_tuser <= depar_out_tuser_next;
		depar_out_tlast <= depar_out_tlast_next;
		depar_out_tvalid <= depar_out_tvalid_next;
	end
end


//===================== sub deparser
generate
	genvar index;
	for (index=0; index<10; index=index+1) 
	begin: sub_op
		sub_deparser #(
			.C_PKT_VEC_WIDTH(),
			.C_PARSE_ACT_LEN()
		)
		sub_deparser (
			.clk				(clk),
			.aresetn			(aresetn),
			.parse_act_valid	(sub_depar_act_valid[index]),
			.parse_act			(parse_action[index][5:0]),
			.phv_in				(phv_fifo_out),
			.val_out_valid		(sub_depar_val_out_valid[index]),
			.val_out			(sub_depar_val_out[index]),
			.val_out_type		(sub_depar_val_out_type[index])
		);
	end
endgenerate


/*================Control Path====================*/
wire [7:0]          mod_id; //module ID
wire [15:0]         control_flag; //dst udp port num
reg  [7:0]          c_index; //table index(addr)
reg                 c_wr_en; //enable table write(wen)

reg [159:0]         entry_reg;

reg [2:0]           c_state;

localparam IDLE_C = 1,
           WRITE_C = 2,
           SU_WRITE_C = 3;

assign mod_id = ctrl_s_axis_tdata[368+:8];
assign control_flag = ctrl_s_axis_tdata[335:320];

//LE to BE switching
wire[C_AXIS_DATA_WIDTH-1:0] ctrl_s_axis_tdata_swapped;
assign ctrl_s_axis_tdata_swapped = {ctrl_s_axis_tdata[0+:8],
									ctrl_s_axis_tdata[8+:8],
									ctrl_s_axis_tdata[16+:8],
									ctrl_s_axis_tdata[24+:8],
									ctrl_s_axis_tdata[32+:8],
									ctrl_s_axis_tdata[40+:8],
									ctrl_s_axis_tdata[48+:8],
									ctrl_s_axis_tdata[56+:8],
									ctrl_s_axis_tdata[64+:8],
									ctrl_s_axis_tdata[72+:8],
									ctrl_s_axis_tdata[80+:8],
									ctrl_s_axis_tdata[88+:8],
									ctrl_s_axis_tdata[96+:8],
									ctrl_s_axis_tdata[104+:8],
									ctrl_s_axis_tdata[112+:8],
									ctrl_s_axis_tdata[120+:8],
									ctrl_s_axis_tdata[128+:8],
									ctrl_s_axis_tdata[136+:8],
									ctrl_s_axis_tdata[144+:8],
									ctrl_s_axis_tdata[152+:8],
									ctrl_s_axis_tdata[160+:8],
									ctrl_s_axis_tdata[168+:8],
									ctrl_s_axis_tdata[176+:8],
									ctrl_s_axis_tdata[184+:8],
									ctrl_s_axis_tdata[192+:8],
									ctrl_s_axis_tdata[200+:8],
									ctrl_s_axis_tdata[208+:8],
									ctrl_s_axis_tdata[216+:8],
									ctrl_s_axis_tdata[224+:8],
									ctrl_s_axis_tdata[232+:8],
									ctrl_s_axis_tdata[240+:8],
									ctrl_s_axis_tdata[248+:8],
                                    ctrl_s_axis_tdata[256+:8],
                                    ctrl_s_axis_tdata[264+:8],
                                    ctrl_s_axis_tdata[272+:8],
                                    ctrl_s_axis_tdata[280+:8],
                                    ctrl_s_axis_tdata[288+:8],
                                    ctrl_s_axis_tdata[296+:8],
                                    ctrl_s_axis_tdata[304+:8],
                                    ctrl_s_axis_tdata[312+:8],
                                    ctrl_s_axis_tdata[320+:8],
                                    ctrl_s_axis_tdata[328+:8],
                                    ctrl_s_axis_tdata[336+:8],
                                    ctrl_s_axis_tdata[344+:8],
                                    ctrl_s_axis_tdata[352+:8],
                                    ctrl_s_axis_tdata[360+:8],
                                    ctrl_s_axis_tdata[368+:8],
                                    ctrl_s_axis_tdata[376+:8],
                                    ctrl_s_axis_tdata[384+:8],
                                    ctrl_s_axis_tdata[392+:8],
                                    ctrl_s_axis_tdata[400+:8],
                                    ctrl_s_axis_tdata[408+:8],
                                    ctrl_s_axis_tdata[416+:8],
                                    ctrl_s_axis_tdata[424+:8],
                                    ctrl_s_axis_tdata[432+:8],
                                    ctrl_s_axis_tdata[440+:8],
                                    ctrl_s_axis_tdata[448+:8],
                                    ctrl_s_axis_tdata[456+:8],
                                    ctrl_s_axis_tdata[464+:8],
                                    ctrl_s_axis_tdata[472+:8],
                                    ctrl_s_axis_tdata[480+:8],
                                    ctrl_s_axis_tdata[488+:8],
                                    ctrl_s_axis_tdata[496+:8],
                                    ctrl_s_axis_tdata[504+:8]
                                };

always @(posedge clk or negedge aresetn) begin
    if(~aresetn) begin
        c_wr_en <= 1'b0;
        c_index <= 4'b0;
        entry_reg <= 0;

        c_state <= IDLE_C;
    end
    else begin
        case(c_state)
            IDLE_C: begin
                if(ctrl_s_axis_tvalid && mod_id[2:0] == DEPARSER_MOD_ID && control_flag == 16'hf2f1)begin
                    c_wr_en <= 1'b0;
                    c_index <= ctrl_s_axis_tdata[384+:8];

                    c_state <= WRITE_C;

                end
                else begin
                    c_wr_en <= 1'b0;
                    c_index <= 4'b0; 
                    entry_reg <= 0;

                    c_state <= IDLE_C;
                end
            end  
//support full table flush
            WRITE_C: begin
                if(ctrl_s_axis_tvalid) begin
                    c_wr_en <= 1'b1;
                    entry_reg <= ctrl_s_axis_tdata_swapped[511 -: 160];
                    if(ctrl_s_axis_tlast) begin
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
                if(ctrl_s_axis_tvalid) begin
                    entry_reg <= ctrl_s_axis_tdata_swapped[511 -: 160];
                    c_wr_en <= 1'b1;
                    c_index <= c_index + 1'b1;
                    if(ctrl_s_axis_tlast) begin
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


parse_act_ram_ip
parse_act_ram
(
	// write port
	.clka		(clk),
	.addra		(c_index[4:0]),
	.dina		(entry_reg),
	.ena		(1'b1),
	.wea		(c_wr_en),

	//
	.clkb		(clk),
	.addrb		(vlan_id[8:4]), // TODO: note that we may change due to little or big endian
	.doutb		(bram_out),
	.enb		(1'b1) // always set to 1
);


endmodule
