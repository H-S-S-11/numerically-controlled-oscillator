from nmigen import *
from nmigen.back.pysim import *

import math

def gen_lookup(entry, input_width, output_width):
    #map the inputs to a normal phase
    phase = 2.0*math.pi*(entry/(2**input_width))
    sin_phi = math.sin(phase)
    #map the output to a range of uints
    output = int((sin_phi+1)*(2**output_width)/2)
    return output

def calc_phi_inc(desired_freq, clock_freq):
    max_inc = 2**31 #this would result in output frequency of fclk/2
    ratio = desired_freq/(clock_freq/2)
    return int(ratio*max_inc)

class NCO_LUT(Elaboratable):
    def __init__(self, sin_input_width=8, output_width=8):
        self.phi_inc_i = Signal(31)
        self.sine_wave_o = Signal(output_width)

        self.sin_input_width = sin_input_width
        self.output_width = output_width

    def elaborate(self, platform):
        m = Module()

        sin_o = self.sine_wave_o
        input_width = self.sin_input_width
        output_width = self.output_width

        phi = Signal(32)
        m.d.sync += phi.eq(phi + self.phi_inc_i)

        table_entry = Signal(input_width)
        m.d.comb += table_entry.eq(phi[32-input_width:32])

        with m.Switch(table_entry):
            for entry in range(0, 2**input_width):
                with m.Case(entry):
                    m.d.sync += sin_o.eq(gen_lookup(entry, input_width, output_width))

        return m

if __name__ == "__main__":

    dut = NCO_LUT(16, 16)
    sim = Simulator(dut)
    sim.add_clock(1e-7) #10MHz

    def clock():
        while True:
            yield

    def input_freq():
        phi_inc = calc_phi_inc(200000, 10000000) #200kHz
        yield dut.phi_inc_i.eq(phi_inc)

    sim.add_sync_process(clock)
    sim.add_sync_process(input_freq)

    with sim.write_vcd("NCO_LUT_waves.vcd"):
        sim.run_until(1e-4)