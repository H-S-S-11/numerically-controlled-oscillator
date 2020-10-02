import os
import sys
from nmigen import *
from nmigen.back.pysim import *
from nmigen.back.verilog import *
from nmigen.build import *
from nmigen.build.res import *
from nmigen.lib.io import Pin
from nmigen_boards.de4 import DE4Platform

from nco_lut import *
from pwm import PWM

class Tone_synth(Elaboratable):
    def __init__(self, tone_frequency=440, clk_frequency=50000000, resolution = 8, pwm_resolution=None):
        self.pwm_o = Pin(1, "o")

        self.phi_inc = calc_phi_inc(tone_frequency, clk_frequency)

        self.resolution = resolution
        if pwm_resolution==None:
            self.pwm_resolution = resolution
        else:
            self.pwm_resolution = pwm_resolution
            
    def elaborate(self, platform):
        m = Module()

        m.submodules.nco = self.nco = nco = NCO_LUT(output_width= self.pwm_resolution, sin_input_width=self.resolution)
        m.submodules.pwm = self.pwm = pwm = PWM(resolution = self.pwm_resolution)
    
    
        platform.add_resources([
            Resource("pwm", 0,
                Pins("1", conn=("gpio", 0), dir ="o" ), 
                Attrs(io_standard="3.0-V PCI")
                ),
        ])

        self.pwm_o = platform.request("pwm")

        m.d.comb += [
            nco.phi_inc_i.eq(self.phi_inc),
            pwm.input_value_i.eq(nco.sine_wave_o),
            pwm.write_enable_i.eq(0),
            self.pwm_o.o.eq(pwm.pwm_o),
        ]


        return m

if __name__ == "__main__":
  
    tone = Tone_synth(resolution = 10, pwm_resolution=8)

    if sys.argv[1] == "convert":
        path = "tone_synth_outputs"
        if not os.path.exists(path):
            os.makedirs(path)    
        out = open("tone_synth_outputs/tone_synth.v", "w")
        out.write(convert(tone, ports=[tone.pwm_o.o]))

    elif sys.argv[1] == "build":
        DE4Platform().build(tone, do_program=False)
    elif sys.argv[1] == "program":
        DE4Platform().build(tone, do_program=True)
   