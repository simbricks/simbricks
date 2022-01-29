`timescale 1ns / 1ps

module output_arbiter #(
	parameter C_AXIS_DATA_WIDTH=256,
	parameter C_AXIS_TUSER_WIDTH=128,
	parameter C_NUM_QUEUES=4,
	parameter C_NUM_QUEUES_WIDTH=2
)
(
	input									axis_clk,
	input									aresetn,

	// output
	output [C_AXIS_DATA_WIDTH-1:0]			m_axis_tdata,
	output [C_AXIS_DATA_WIDTH/8-1:0]		m_axis_tkeep,
	output [C_AXIS_TUSER_WIDTH-1:0]			m_axis_tuser,
	output									m_axis_tvalid,
	output									m_axis_tlast,
	input									m_axis_tready,

	// input
	input [C_AXIS_DATA_WIDTH-1:0]			s_axis_tdata_0,
	input [C_AXIS_DATA_WIDTH/8-1:0]			s_axis_tkeep_0,
	input [C_AXIS_TUSER_WIDTH-1:0]			s_axis_tuser_0,
	input									s_axis_tlast_0,
	input									s_axis_tvalid_0,
	output									s_axis_tready_0,

	input [C_AXIS_DATA_WIDTH-1:0]			s_axis_tdata_1,
	input [C_AXIS_DATA_WIDTH/8-1:0]			s_axis_tkeep_1,
	input [C_AXIS_TUSER_WIDTH-1:0]			s_axis_tuser_1,
	input									s_axis_tlast_1,
	input									s_axis_tvalid_1,
	output									s_axis_tready_1,

	input [C_AXIS_DATA_WIDTH-1:0]			s_axis_tdata_2,
	input [C_AXIS_DATA_WIDTH/8-1:0]			s_axis_tkeep_2,
	input [C_AXIS_TUSER_WIDTH-1:0]			s_axis_tuser_2,
	input									s_axis_tlast_2,
	input									s_axis_tvalid_2,
	output									s_axis_tready_2,

	input [C_AXIS_DATA_WIDTH-1:0]			s_axis_tdata_3,
	input [C_AXIS_DATA_WIDTH/8-1:0]			s_axis_tkeep_3,
	input [C_AXIS_TUSER_WIDTH-1:0]			s_axis_tuser_3,
	input									s_axis_tlast_3,
	input									s_axis_tvalid_3,
	output									s_axis_tready_3
);

wire [C_NUM_QUEUES-1:0]					nearly_full;
wire [C_NUM_QUEUES-1:0]					empty;
wire [C_AXIS_DATA_WIDTH-1:0]			in_tdata [C_NUM_QUEUES-1:0];
wire [C_AXIS_DATA_WIDTH/8-1:0]			in_tkeep [C_NUM_QUEUES-1:0];
wire [C_AXIS_TUSER_WIDTH-1:0]			in_tuser [C_NUM_QUEUES-1:0];
wire [C_NUM_QUEUES-1:0]					in_tvalid;
wire [C_NUM_QUEUES-1:0]					in_tlast;

wire [C_AXIS_DATA_WIDTH-1:0]			fifo_out_tdata [C_NUM_QUEUES-1:0];
wire [C_AXIS_DATA_WIDTH/8-1:0]			fifo_out_tkeep [C_NUM_QUEUES-1:0];
wire [C_AXIS_TUSER_WIDTH-1:0]			fifo_out_tuser [C_NUM_QUEUES-1:0];
wire [C_NUM_QUEUES-1:0]					fifo_out_tlast;

reg [C_NUM_QUEUES-1:0]					rd_en;
wire [C_NUM_QUEUES_WIDTH-1:0]			cur_queue_plus1;
reg [C_NUM_QUEUES_WIDTH-1:0]			cur_queue, cur_queue_next;

reg										state, state_next;



generate
	genvar i;
	for (i=0; i<C_NUM_QUEUES; i=i+1) begin:
		out_arb_queues
		fallthrough_small_fifo #(
			.WIDTH(C_AXIS_DATA_WIDTH+C_AXIS_DATA_WIDTH/8+C_AXIS_TUSER_WIDTH+1),
			.MAX_DEPTH_BITS(4)
		) out_arb_fifo (
			.dout			({fifo_out_tdata[i], fifo_out_tuser[i], fifo_out_tkeep[i], fifo_out_tlast[i]}),
			.rd_en			(rd_en[i]),

			.din			({in_tdata[i], in_tuser[i], in_tkeep[i], in_tlast[i]}),
			.wr_en			(in_tvalid[i] & ~nearly_full[i]),

			.full			(),
			.nearly_full	(nearly_full[i]),
			.empty			(empty[i]),
			.reset			(~aresetn),
			.clk			(axis_clk)
		);
	end
endgenerate

assign in_tdata[0] = s_axis_tdata_0;
assign in_tkeep[0] = s_axis_tkeep_0;
assign in_tuser[0] = s_axis_tuser_0;
assign in_tlast[0] = s_axis_tlast_0;
assign in_tvalid[0] = s_axis_tvalid_0;
assign s_axis_tready_0 = ~nearly_full[0];

assign in_tdata[1] = s_axis_tdata_1;
assign in_tkeep[1] = s_axis_tkeep_1;
assign in_tuser[1] = s_axis_tuser_1;
assign in_tlast[1] = s_axis_tlast_1;
assign in_tvalid[1] = s_axis_tvalid_1;
assign s_axis_tready_1 = ~nearly_full[1];

assign in_tdata[2] = s_axis_tdata_2;
assign in_tkeep[2] = s_axis_tkeep_2;
assign in_tuser[2] = s_axis_tuser_2;
assign in_tlast[2] = s_axis_tlast_2;
assign in_tvalid[2] = s_axis_tvalid_2;
assign s_axis_tready_2 = ~nearly_full[2];

assign in_tdata[3] = s_axis_tdata_3;
assign in_tkeep[3] = s_axis_tkeep_3;
assign in_tuser[3] = s_axis_tuser_3;
assign in_tlast[3] = s_axis_tlast_3;
assign in_tvalid[3] = s_axis_tvalid_3;
assign s_axis_tready_3 = ~nearly_full[3];

assign cur_queue_plus1 = (cur_queue==C_NUM_QUEUES-1)? 0 : cur_queue+1;

assign m_axis_tdata = fifo_out_tdata[cur_queue];
assign m_axis_tuser = fifo_out_tuser[cur_queue];
assign m_axis_tkeep = fifo_out_tkeep[cur_queue];
assign m_axis_tlast = fifo_out_tlast[cur_queue];
assign m_axis_tvalid = ~empty[cur_queue] && m_axis_tready;

localparam	IDLE=0,
			WR_PKT=1;

always @(*) begin

	state_next = state;
	cur_queue_next = cur_queue;
	rd_en = 0;

	case (state)
		IDLE: begin
			if (!empty[cur_queue]) begin
				if (m_axis_tready) begin
					state_next = WR_PKT;
					rd_en[cur_queue] = 1;
				end
			end
			else begin
				cur_queue_next = cur_queue_plus1;
			end
		end
		WR_PKT: begin
			if (m_axis_tready & m_axis_tlast) begin
				state_next = IDLE;
				rd_en[cur_queue] = 1;
				cur_queue_next = cur_queue_plus1;
			end
			else if (m_axis_tready && !empty[cur_queue]) begin
				rd_en[cur_queue] = 1;
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

endmodule
