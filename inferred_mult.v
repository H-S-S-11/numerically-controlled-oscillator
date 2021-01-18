// Macc with registered inputs as per UG626
// note that a faster version would also use
// registers on the multiply output, for one extra latency cycle

module dsp48e_macc_latency1_16bit(
    input reg clk, rst_sync,
    input reg [15:0] a, b,
    output reg [47:0] accumulator
)
reg [15:0] a_reg, b_reg;

always @(posedge clk) begin
    if(rst_sync) begin
        accumulator <= 0;
        a_reg <= 0;
        b_reg <= 0;
    end else begin
        a_reg <= a;
        b_reg <= b;
        accumulator <= accumulator + (a_reg*b_reg);
    end
end

endmodule