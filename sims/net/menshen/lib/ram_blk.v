module ram_blk #(
    parameter ADDR_BITS = 5,
    parameter DATA_BITS = 32
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

    reg [(DATA_BITS - 1):0] ram [(ADDR_BITS - 1):0];
    //reg [(ADDR_BITS - 1):0] read_addrb;
    reg [(DATA_BITS - 1):0] doutb_r;
 
    always @(posedge clka) begin
        if (ena) begin
            if (wea)
                ram[addra] <= dina;
            //read_addra <= addra;
        end
    end

    /*always @(posedge clkb) begin
        if (enb)  
            doutb_r <= ram[addrb];  
    end
    assign doutb = doutb_r;
    */
  //assign douta = ram[read_addra];
  assign doutb = ram[addrb];
  //
endmodule