from nmigen import *
from nmigen.sim import *
from utility.bram_inst import *
from nco_lut import *
import math

def twos_complement(decimal, bits):
    if(decimal >= 0):
        return decimal
    else:
        inverted = 2**bits + decimal
        return twos_complement(inverted, bits)

def generate_init_data(data_width, addr_width, signed_output = True):
    init_data = {}
    for line in range(0, 64):  # 64 for 18k BRAM
        init_line = 0
        for word in range(0, 8):
            decimal = gen_lookup((line*8 + word), addr_width, data_width, signed_output=signed_output)
            if signed_output:
                decimal = twos_complement(decimal, data_width)
            init_line += (decimal << word*32)
        line_string = str(hex(line)).upper()[2:]
        while len(line_string) < 2:
            line_string = '0' + line_string
        init_data['p_INIT_'+ line_string] = init_line
    return init_data
 
class NCO_LUT_Pipelined(Elaboratable):
    # Instantiates a BRAM with the data output register to achieve much higher frequencies than
    # otherwise possible (with inferred ROM), up to the BRAM Fmax when tested
    def __init__(self, output_width=8, sin_input_width=None, signed_output=True):
        self.phi_inc_i = Signal(31)

        self.signed_output = signed_output
        if (signed_output):
            self.sine_wave_o = Signal(shape=signed(output_width))
        else:
            self.sine_wave_o = Signal(shape=unsigned(output_width))
        
        self.output_width = output_width
        if sin_input_width:
            self.sin_input_width = sin_input_width
        else:
            self.sin_input_width = output_width

    def elaborate(self, platform):
        m = Module()

        input_width = self.sin_input_width
        output_width = self.output_width

        phi = Signal(32)
        table_entry = Signal(input_width)
        m.d.sync += phi.eq(phi + self.phi_inc_i)        
        m.d.comb += table_entry.eq(phi[32-input_width:32])

        init = generate_init_data(output_width, input_width)
        m.submodules.brom = brom = BROMWrapper(init)
        m.d.sync += [
            self.sine_wave_o.eq(brom.read_port[0:output_width]),
            brom.address.eq(table_entry),
        ]

        return m

if __name__ == "__main__":
    print("No sim model of BRAM primitive, cannot simulate")