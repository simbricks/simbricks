`timescale 1ns / 1ps


module parser_top #(
	parameter C_S_AXIS_DATA_WIDTH = 512,
	parameter C_S_AXIS_TUSER_WIDTH = 128,
	parameter PKT_HDR_LEN = (6+4+2)*8*8+256, // check with the doc
	parameter PARSER_MOD_ID = 3'b0,
	parameter C_NUM_SEGS = 2,
	parameter C_VLANID_WIDTH = 12,
	parameter C_PARSER_RAM_WIDTH = 160
)
(
	input									axis_clk,
	input									aresetn,

	// input slvae axi stream
	input [C_S_AXIS_DATA_WIDTH-1:0]			s_axis_tdata,
	input [C_S_AXIS_TUSER_WIDTH-1:0]		s_axis_tuser,
	input [C_S_AXIS_DATA_WIDTH/8-1:0]		s_axis_tkeep,
	input									s_axis_tvalid,
	input									s_axis_tlast,
	// input vlan info
	input [C_VLANID_WIDTH-1:0]				s_vlan_id,
	input									s_vlan_id_valid,

	// output
	output reg								parser_valid,
	output reg [PKT_HDR_LEN-1:0]			pkt_hdr_vec,

	// back-pressure signals
	output									s_axis_tready,
	input									stg_ready_in,

	// output vlan
	output reg[C_VLANID_WIDTH-1:0]				out_vlan,
	output reg									out_vlan_valid,
	input									out_vlan_ready,

	// output to different pkt fifo queues (i.e., data cache)
	output [C_S_AXIS_DATA_WIDTH-1:0]		m_axis_tdata_0,
	output [C_S_AXIS_TUSER_WIDTH-1:0]		m_axis_tuser_0,
	output [C_S_AXIS_DATA_WIDTH/8-1:0]		m_axis_tkeep_0,
	output									m_axis_tlast_0,
	output									m_axis_tvalid_0,
	input									m_axis_tready_0,

	output [C_S_AXIS_DATA_WIDTH-1:0]		m_axis_tdata_1,
	output [C_S_AXIS_TUSER_WIDTH-1:0]		m_axis_tuser_1,
	output [C_S_AXIS_DATA_WIDTH/8-1:0]		m_axis_tkeep_1,
	output									m_axis_tlast_1,
	output									m_axis_tvalid_1,
	input									m_axis_tready_1,

	output [C_S_AXIS_DATA_WIDTH-1:0]		m_axis_tdata_2,
	output [C_S_AXIS_TUSER_WIDTH-1:0]		m_axis_tuser_2,
	output [C_S_AXIS_DATA_WIDTH/8-1:0]		m_axis_tkeep_2,
	output									m_axis_tlast_2,
	output									m_axis_tvalid_2,
	input									m_axis_tready_2,

	output [C_S_AXIS_DATA_WIDTH-1:0]		m_axis_tdata_3,
	output [C_S_AXIS_TUSER_WIDTH-1:0]		m_axis_tuser_3,
	output [C_S_AXIS_DATA_WIDTH/8-1:0]		m_axis_tkeep_3,
	output									m_axis_tlast_3,
	output									m_axis_tvalid_3,
	input									m_axis_tready_3,

	// ctrl path
	input [C_S_AXIS_DATA_WIDTH-1:0]			ctrl_s_axis_tdata,
	input [C_S_AXIS_TUSER_WIDTH-1:0]		ctrl_s_axis_tuser,
	input [C_S_AXIS_DATA_WIDTH/8-1:0]		ctrl_s_axis_tkeep,
	input									ctrl_s_axis_tvalid,
	input									ctrl_s_axis_tlast,

	output reg [C_S_AXIS_DATA_WIDTH-1:0]		ctrl_m_axis_tdata,
	output reg [C_S_AXIS_TUSER_WIDTH-1:0]		ctrl_m_axis_tuser,
	output reg [C_S_AXIS_DATA_WIDTH/8-1:0]		ctrl_m_axis_tkeep,
	output reg									ctrl_m_axis_tvalid,
	output reg									ctrl_m_axis_tlast
);

wire [C_NUM_SEGS*C_S_AXIS_DATA_WIDTH-1:0]	segs_in;
reg [C_NUM_SEGS*C_S_AXIS_DATA_WIDTH-1:0]	segs_in_r;
wire [C_S_AXIS_TUSER_WIDTH-1:0]				tuser_1st_in;
reg [C_S_AXIS_TUSER_WIDTH-1:0]				tuser_1st_in_r;
wire										segs_in_valid;
reg											segs_in_valid_r;



// paser bram out
wire [C_PARSER_RAM_WIDTH-1:0]	bram_out_0;
reg [C_PARSER_RAM_WIDTH-1:0]	bram_out_0_d1;
reg								out_bram_valid, out_bram_valid_d1;
reg bram_ready, bram_ready_next;


assign s_axis_tready = bram_ready
						&& m_axis_tready_0
						&& m_axis_tready_1
						&& m_axis_tready_2
						&& m_axis_tready_3;
//

wire [3:0] m_axis_tready_queue;

assign m_axis_tready_queue[0] = m_axis_tready_0;
assign m_axis_tready_queue[1] = m_axis_tready_1;
assign m_axis_tready_queue[2] = m_axis_tready_2;
assign m_axis_tready_queue[3] = m_axis_tready_3;


localparam	IDLE=0,
			FLUSH_REST_PKTS=1;
reg [1:0] state, state_next;
reg [1:0] cur_queue, cur_queue_next;
wire [1:0] cur_queue_plus1;

assign cur_queue_plus1 = (cur_queue==3)?0:cur_queue+1;

// ==================================================
assign m_axis_tdata_0 = s_axis_tdata;
assign m_axis_tuser_0 = s_axis_tuser;
assign m_axis_tkeep_0 = s_axis_tkeep;
assign m_axis_tlast_0 = s_axis_tlast;
assign m_axis_tvalid_0 = (cur_queue==0?1:0) & s_axis_tvalid & m_axis_tready_0;

assign m_axis_tdata_1 = s_axis_tdata;
assign m_axis_tuser_1 = s_axis_tuser;
assign m_axis_tkeep_1 = s_axis_tkeep;
assign m_axis_tlast_1 = s_axis_tlast;
assign m_axis_tvalid_1 = (cur_queue==1?1:0) & s_axis_tvalid & m_axis_tready_1;

assign m_axis_tdata_2 = s_axis_tdata;
assign m_axis_tuser_2 = s_axis_tuser;
assign m_axis_tkeep_2 = s_axis_tkeep;
assign m_axis_tlast_2 = s_axis_tlast;
assign m_axis_tvalid_2 = (cur_queue==2?1:0) & s_axis_tvalid & m_axis_tready_2;

assign m_axis_tdata_3 = s_axis_tdata;
assign m_axis_tuser_3 = s_axis_tuser;
assign m_axis_tkeep_3 = s_axis_tkeep;
assign m_axis_tlast_3 = s_axis_tlast;
assign m_axis_tvalid_3 = (cur_queue==3?1:0) & s_axis_tvalid & m_axis_tready_3;
// ==================================================


always @(*) begin
	state_next = state;
	cur_queue_next = cur_queue;

	case (state)
		IDLE: begin
			if (s_axis_tvalid) begin
				if (m_axis_tready_queue[cur_queue]) begin

					if (!s_axis_tlast) begin
						state_next = FLUSH_REST_PKTS;
					end
					else begin
						cur_queue_next = cur_queue_plus1;
					end
				end
			end
		end
		FLUSH_REST_PKTS: begin
			if (s_axis_tvalid) begin
				if (m_axis_tready_queue[cur_queue]) begin

					if (s_axis_tlast) begin
						cur_queue_next = cur_queue_plus1;
						state_next = IDLE;
					end
				end
			end
		end
	endcase
end

always @(posedge axis_clk) begin
	if (~aresetn) begin
		state <= IDLE;
		cur_queue <= 0;
	end
	else begin
		state <= state_next;
		cur_queue <= cur_queue_next;
	end
end

// ==================================================

wire [C_VLANID_WIDTH-1:0]				parser_out_vlan, vlan_fifo_out;
wire									parser_out_vlan_valid;
// wire	vlan_fifo_empty, vlan_fifo_nearly_full;
reg [C_VLANID_WIDTH-1:0] out_vlan_next;
reg out_vlan_valid_next;
// reg		vlan_fifo_rd_en;

// wire [PKT_HDR_LEN-1:0]		phv_fifo_out;
// wire	phv_fifo_empty, phv_fifo_nearly_full;
// reg		phv_fifo_rd_en;



localparam P_IDLE=0;

reg [1:0] p_state, p_state_next;
reg [1:0] p_cur_queue, p_cur_queue_next;
wire [1:0] p_cur_queue_plus1;

assign p_cur_queue_plus1 = (p_cur_queue==3)?0:p_cur_queue+1;

wire [3:0] p_cur_queue_val;
assign p_cur_queue_val[0] = (p_cur_queue==0)?1:0;
assign p_cur_queue_val[1] = (p_cur_queue==1)?1:0;
assign p_cur_queue_val[2] = (p_cur_queue==2)?1:0;
assign p_cur_queue_val[3] = (p_cur_queue==3)?1:0;

wire parser_valid_w;
wire [PKT_HDR_LEN-1:0] pkt_hdr_vec_w;
reg [PKT_HDR_LEN-1:0] pkt_hdr_vec_next, pkt_hdr_vec_r;
reg parser_valid_next, parser_valid_r;

/*
always @(*) begin
	p_state_next = p_state;
	p_cur_queue_next = p_cur_queue;
	
	pkt_hdr_vec_next = pkt_hdr_vec;
	parser_valid_next = 0;
	case (p_state)
		P_IDLE: begin
			if (parser_valid_w) begin
				pkt_hdr_vec_next = {pkt_hdr_vec_w[PKT_HDR_LEN-1:145], p_cur_queue_val, pkt_hdr_vec_w[0+:141]};
				parser_valid_next = 1;

				p_cur_queue_next = p_cur_queue_plus1;
			end
		end
	endcase
end*/

always @(*) begin
	p_cur_queue_next = p_cur_queue;
	pkt_hdr_vec_next = pkt_hdr_vec_r;
	parser_valid_next = 0;

	if (parser_valid_w) begin
		pkt_hdr_vec_next = {pkt_hdr_vec_w[PKT_HDR_LEN-1:145], p_cur_queue_val, pkt_hdr_vec_w[0+:141]};
		parser_valid_next = 1;

		p_cur_queue_next = p_cur_queue_plus1;
	end
end

always @(*) begin
	out_vlan_valid_next = 0;
	out_vlan_next = out_vlan;

	if (parser_out_vlan_valid) begin
		out_vlan_valid_next = 1;
		out_vlan_next = parser_out_vlan;
	end
end

always @(posedge axis_clk) begin
	if (~aresetn) begin
		p_state <= P_IDLE;
		p_cur_queue <= 0;
		pkt_hdr_vec <= 0;
		parser_valid <= 0;

		out_vlan <= 0;
		out_vlan_valid <= 0;

		pkt_hdr_vec_r <= 0;
		parser_valid_r <= 0;
	end
	else begin
		p_state <= p_state_next;
		p_cur_queue <= p_cur_queue_next;
		pkt_hdr_vec_r <= pkt_hdr_vec_next;
		parser_valid_r <= parser_valid_next;
		pkt_hdr_vec <= pkt_hdr_vec_r;
		parser_valid <= parser_valid_r;

		out_vlan <= out_vlan_next;
		out_vlan_valid <= out_vlan_valid_next;
	end
end

//
always @(posedge axis_clk) begin
	if (~aresetn) begin
		segs_in_r <= 0;
		tuser_1st_in_r <= 0;
		segs_in_valid_r <= 0;
	end
	else begin
		segs_in_r <= segs_in;
		tuser_1st_in_r <= tuser_1st_in;
		segs_in_valid_r <= segs_in_valid;
	end
end

//
parser_wait_segs #(
)
get_segs
(
	.axis_clk				(axis_clk),
	.aresetn				(aresetn),

	.s_axis_tdata			(s_axis_tdata),
	.s_axis_tuser			(s_axis_tuser),
	.s_axis_tkeep			(s_axis_tkeep),
	.s_axis_tvalid			(s_axis_tvalid),
	.s_axis_tlast			(s_axis_tlast),

	// output
	.tdata_segs				(segs_in),
	.tuser_1st				(tuser_1st_in),
	.segs_valid				(segs_in_valid)
);

parser_do_parsing_top #(
)
do_parsing
(
	.clk					(axis_clk),
	.aresetn				(aresetn),

	.segs_in				(segs_in_r),
	.segs_in_valid			(segs_in_valid_r),
	.tuser_1st_in			(tuser_1st_in_r),
	.bram_in				(bram_out_0_d1),
	.bram_in_valid			(out_bram_valid_d1),

	.stg_ready				(stg_ready_in),
	.stg_vlan_ready			(out_vlan_ready),

	// output
	.pkt_hdr_vec			(pkt_hdr_vec_w),
	.parser_valid			(parser_valid_w),
	.vlan_out				(parser_out_vlan),
	.vlan_out_valid			(parser_out_vlan_valid)
);

//
localparam	BRAM_IDLE=0,
			BRAM_CYCLE_1=1,
			BRAM_CYCLE_2=2,
			BRAM_CYCLE_3=3;

reg [2:0] bram_state, bram_state_next;
reg out_bram_valid_next;

always @(*) begin
	bram_state_next = bram_state;

	out_bram_valid_next = 0;

	bram_ready_next = bram_ready;
	case (bram_state) 
		BRAM_IDLE: begin
			if (s_vlan_id_valid) begin
				bram_state_next = BRAM_CYCLE_1;
				if (s_axis_tvalid && s_axis_tlast) begin
					bram_ready_next = 0;
				end
			end
		end
		BRAM_CYCLE_1: begin
			bram_state_next = BRAM_IDLE;
			out_bram_valid_next = 1;
			bram_ready_next = 1;
		end
	endcase
end

always @(posedge axis_clk) begin
	if (~aresetn) begin
		bram_state <= BRAM_IDLE;

		out_bram_valid <= 0;
		bram_ready <= 1;
		out_bram_valid_d1 <= 0;
	end
	else begin

		bram_state <= bram_state_next;
		out_bram_valid <= out_bram_valid_next;
		out_bram_valid_d1 <= out_bram_valid;
		bram_out_0_d1 <= bram_out_0;
		bram_ready <= bram_ready_next;
	end
end

// fifo
/*
fallthrough_small_fifo #(
	.WIDTH(PKT_HDR_LEN),
	.MAX_DEPTH_BITS(4)
)
pkt_hdr_fifo (
	.din				(pkt_hdr_vec_w),
	.wr_en				(parser_valid_w),
	
	.dout				(phv_fifo_out),
	.rd_en				(phv_fifo_rd_en),
	.full				(),
	.nearly_full		(phv_fifo_nearly_full),
	.empty				(phv_fifo_empty),
	.reset				(~aresetn),
	.clk				(axis_clk)
);

fallthrough_small_fifo #(
	.WIDTH(C_VLANID_WIDTH),
	.MAX_DEPTH_BITS(4)
)
vlan_fifo (
	.din				(parser_out_vlan),
	.wr_en				(parser_out_vlan_valid),
	
	.dout				(vlan_fifo_out),
	.rd_en				(vlan_fifo_rd_en),
	.full				(),
	.nearly_full		(vlan_fifo_nearly_full),
	.empty				(vlan_fifo_empty),
	.reset				(~aresetn),
	.clk				(axis_clk)
);*/

/*================Control Path====================*/
wire [7:0]          mod_id; //module ID
wire [15:0]         control_flag; //dst udp port num
reg  [7:0]          c_index; //table index(addr)
reg                 c_wr_en; //enable table write(wen)
reg  [159:0]        entry_reg;

reg  [2:0]          c_state;

localparam IDLE_C = 1,
           WRITE_C  =2,
           SU_WRITE_C = 3;

assign mod_id = ctrl_s_axis_tdata[368+:8];
assign control_flag = ctrl_s_axis_tdata[335:320];

//LE to BE switching
wire[C_S_AXIS_DATA_WIDTH-1:0] ctrl_s_axis_tdata_swapped;
assign ctrl_s_axis_tdata_swapped = {	ctrl_s_axis_tdata[0+:8],
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

always @(posedge axis_clk or negedge aresetn) begin
    if(~aresetn) begin
        c_wr_en <= 1'b0;
        c_index <= 4'b0;

        ctrl_m_axis_tdata <= 0;
        ctrl_m_axis_tuser <= 0;
        ctrl_m_axis_tkeep <= 0;
        ctrl_m_axis_tvalid <= 0;
        ctrl_m_axis_tlast <= 0;
        entry_reg <= 0;

        c_state <= IDLE_C;
    end
    else begin
        case(c_state)
            IDLE_C: begin
                if(ctrl_s_axis_tvalid && mod_id[2:0] == PARSER_MOD_ID && control_flag == 16'hf2f1)begin
                    c_wr_en <= 1'b0;
                    c_index <= ctrl_s_axis_tdata[384+:8];

                    ctrl_m_axis_tdata <= 0;
                    ctrl_m_axis_tuser <= 0;
                    ctrl_m_axis_tkeep <= 0;
                    ctrl_m_axis_tvalid <= 0;
                    ctrl_m_axis_tlast <= 0;

                    c_state <= WRITE_C;

                end
                else begin
                    c_wr_en <= 1'b0;
                    c_index <= 4'b0; 
                    entry_reg <= 0;

                    ctrl_m_axis_tdata <= ctrl_s_axis_tdata;
                    ctrl_m_axis_tuser <= ctrl_s_axis_tuser;
                    ctrl_m_axis_tkeep <= ctrl_s_axis_tkeep;
                    ctrl_m_axis_tvalid <= ctrl_s_axis_tvalid;
                    ctrl_m_axis_tlast <= ctrl_s_axis_tlast;

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


// =============================================================== //
// parse_act_ram_ip #(
// 	.C_INIT_FILE_NAME	("./parse_act_ram_init_file.mif"),
// 	.C_LOAD_INIT_FILE	(1)
// )
parse_act_ram_ip
parse_act_ram_0
(
	// write port
	.clka		(axis_clk),
	.addra		(c_index[4:0]),
	.dina		(entry_reg),
	.ena		(1'b1),
	.wea		(c_wr_en),

	//
	.clkb		(axis_clk),
	.addrb		(s_vlan_id[8:4]), // TODO: note that we may change due to little or big endian
	.doutb		(bram_out_0),
	.enb		(1'b1) // always set to 1
);

endmodule
