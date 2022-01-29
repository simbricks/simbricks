module cam_top #(
    parameter C_DEPTH = 16,
    parameter ADDR_BITS = 4,
    parameter C_WIDTH = 205,
    parameter C_MEM_INIT = 0
) (
    input CLK,
    input RST,
    input [(C_WIDTH-1):0] CMP_DIN,
    input CMP_DATA_MASK,
    output BUSY,
    output MATCH,
    output [(ADDR_BITS - 1):0] MATCH_ADDR,

    input WE,
    input [(ADDR_BITS - 1):0] WR_ADDR,
    input DATA_MASK,
    input [(C_WIDTH-1):0] DIN,
    input EN
);

    cam_simple #(
        .DATA_WIDTH(C_WIDTH),
        .ADDR_WIDTH(ADDR_BITS),
        .SLICE_WIDTH(9)
    ) cam (
        .clk(CLK),
        .rst(RST),

        .write_addr(WR_ADDR),
        .write_data(DIN),
        .write_delete(0),
        .write_enable(WE),
        .write_busy(BUSY),

        .compare_data(CMP_DIN),
        .match_many(),
        .match_single(),
        .match_addr(MATCH_ADDR),
        .match(MATCH)
    );
endmodule
