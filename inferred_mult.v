// Macc with registered inputs as per UG626
// note that a faster version would also use
// registers on the multiply output, for one extra latency cycle

module dsp48e_macc_latency1_16bit(
    input clk, rst_sync,
    input [15:0] a, b,
    output [47:0] accumulator
);

reg [47:0] acc_reg;
reg [15:0] a_reg, b_reg;

assign accumulator = acc_reg;

always @(posedge clk) begin
    if(rst_sync) begin
        acc_reg <= 0;
        a_reg <= 0;
        b_reg <= 0;
    end else begin
        a_reg <= a;
        b_reg <= b;
        acc_reg <= acc_reg + (a_reg*b_reg);
    end
end

endmodule