module cam_simple #(
    parameter DATA_WIDTH = 64,
    parameter ADDR_WIDTH = 5,
    parameter SLICE_WIDTH = 9
)
(
    input  wire                     clk,
    input  wire                     rst,

    input  wire [ADDR_WIDTH-1:0]    write_addr,
    input  wire [DATA_WIDTH-1:0]    write_data,
    input  wire                     write_delete,
    input  wire                     write_enable,
    output wire                     write_busy,

    input  wire [DATA_WIDTH-1:0]    compare_data,
    output wire [2**ADDR_WIDTH-1:0] match_many,
    output wire [2**ADDR_WIDTH-1:0] match_single,
    output wire [ADDR_WIDTH-1:0]    match_addr,
    output wire                     match
);

localparam RAM_DEPTH = 2**ADDR_WIDTH;

reg [RAM_DEPTH - 1 : 0]match_many_raw;
reg valids[RAM_DEPTH];
reg [DATA_WIDTH-1:0]keys[RAM_DEPTH];

// reads
integer k;
always @(posedge clk) begin
    for (k = 0; k < RAM_DEPTH; k = k + 1) begin
        match_many_raw[k] <= valids[k] && (keys[k] == compare_data);
    end
end

// writes
integer i;
always @(posedge clk) begin
    if (rst) begin
        for (i = 0; i < RAM_DEPTH; i = i + 1) begin
            valids[i] <= 0;
            keys[i] <= 0;
        end
    end else if (write_enable) begin
        if (write_delete) begin
            valids[write_addr] <= 0;
        end else begin
            keys[write_addr] <= write_data;
            valids[write_addr] <= 1;
        end
    end
end

priority_encoder #(
    .WIDTH(RAM_DEPTH),
    .LSB_PRIORITY("HIGH")
)
priority_encoder_inst (
    .input_unencoded(match_many_raw),
    .output_valid(match),
    .output_encoded(match_addr),
    .output_unencoded(match_single)
);

endmodule
