from nmigen import *
from nmigen.sim import *
from bram_instantiation import *
import math

def gen_lookup(entry, input_width, output_width, signed_output=True):
    #map the inputs to a normal phase
    phase = 2.0*math.pi*(entry/((2**input_width)-1))
    if signed_output:
        sin_phi = math.sin(phase)/2
    else:
        sin_phi = (math.sin(phase)+1)/2
    #map the output to a range of uints
    output = int((sin_phi)*((2**output_width)-1))
    return output

def calc_phi_inc(desired_freq, clock_freq):
    max_inc = (2**31)-1 #this would result in output frequency of fclk/2
    ratio = desired_freq/(clock_freq/2)
    return int(ratio*max_inc)

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

        sin_o = self.sine_wave_o
        input_width = self.sin_input_width
        output_width = self.output_width

        phi = Signal(32)
        m.d.sync += phi.eq(phi + self.phi_inc_i)

        table_entry = Signal(input_width)
        m.d.comb += table_entry.eq(phi[32-input_width:32])

        init = generate_init_data(self.output_width, self.sin_input_width)
       
        brom = BROMWrapper(init)
        m.submodules.brom = brom
        m.d.comb += [
            sin_o.eq(brom.read_port[0:output_width]),
            brom.address.eq(table_entry),
        ]

        return m

if __name__ == "__main__":

    dut = NCO_LUT_Pipelined(signed_output=True)
    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz

    def clock():
        while True:
            yield

    def input_freq():
        phi_inc = calc_phi_inc(9000000, 100000000) #9MHz
        yield dut.phi_inc_i.eq(phi_inc)

    sim.add_sync_process(clock)
    sim.add_sync_process(input_freq)

    with sim.write_vcd("NCO_LUT_waves.vcd"):
        sim.run_until(1e-5)