from nmigen import *
from nmigen.back.pysim import *

import math

def generate_lookup_table(entry, input_width, output_width):
    #map the inputs to a normal phase
    phase = 2.0*math.pi*(entry/(2**input_width))
    sin_phi = math.sin(phase)
    #map the output to a range of uints
    output = int((sin_phi+1)*(2**output_width)/2)
    return output

class NCO_LUT(Elaboratable):
    def __init__(self, sin_input_width, output_width):
        self.phi_inc_i = Signal(31)
        self.sine_wave_o = Signal(output_width)

    def elaborate(self, platform):
        m = Module()

        phi = Signal(32)
        m.d.sync += phi.eq(phi + self.phi_inc_i)

        

        return m

