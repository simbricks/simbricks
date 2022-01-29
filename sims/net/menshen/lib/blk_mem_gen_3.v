module blk_mem_gen_3 #(
    parameter ADDR_BITS = 5,
    parameter DATA_BITS = 193
)
(
    input [(ADDR_BITS - 1):0] addra,
    input clka,
    input [(DATA_BITS - 1):0] dina,
    input ena,
    input wea,

    input [(ADDR_BITS - 1):0] addrb,
    input clkb,
    output [(DATA_BITS - 1):0] doutb,
    input enb
);

    ram_blk #(
        .ADDR_BITS(ADDR_BITS),
        .DATA_BITS(DATA_BITS)
    ) ram (
        .addra(addra),
        .clka(clka),
        .dina(dina),
        .ena(ena),
        .wea(wea),
        .addrb(addrb),
        .clkb(clkb),
        .doutb(doutb),
        .enb(enb)
    );
endmodule