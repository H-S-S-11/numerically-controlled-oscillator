import os
import sys
from nmigen import *
from nmigen.sim import *
from nmigen.back.verilog import *
from nmigen.build import *
from nmigen.build.res import *
from nmigen.lib.io import Pin
from nmigen_boards.ml505 import ML505Platform

from nco_lut import *
from pwm import PWM
from pdm import PDM

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

        m.submodules.nco = self.nco = nco = NCO_LUT(output_width= self.pwm_resolution, 
            sin_input_width=self.resolution, signed_output=False)
        m.submodules.pwm = self.pwm = pwm = PWM(resolution = self.pwm_resolution)
        m.submodules.pdm = self.pdm = pdm = PDM(resolution = self.pwm_resolution)
    
        if(platform != None):
            platform.add_resources([
                Resource("pwm", 0,
                    Pins("2", conn=("gpio", 0), dir ="o" ), 
                    Attrs(IOSTANDARD="LVCMOS33")
                    ),
            ])
            self.pwm_o = platform.request("pwm")
            dpad = platform.request("dpad")

        m.d.comb += [
            nco.phi_inc_i.eq(self.phi_inc),
            pwm.input_value_i.eq(nco.sine_wave_o),
            pwm.write_enable_i.eq(0),
            pdm.input.eq(nco.sine_wave_o),
            pdm.write_en.eq(1),
            #self.pwm_o.o.eq(pwm.pwm_o),
            self.pwm_o.o.eq( Mux(dpad.c.i, pwm.pwm_o, pdm.pdm_out) ),
        ]

        


        return m

if __name__ == "__main__":
  
    tone = Tone_synth(resolution = 6, pwm_resolution=6, clk_frequency=100000000)

    if sys.argv[1] == "convert":
        path = "tone_synth_outputs"
        if not os.path.exists(path):
            os.makedirs(path)    
        out = open("tone_synth_outputs/tone_synth.v", "w")
        out.write(convert(tone, ports=[tone.pwm_o.o]))

    elif sys.argv[1] == "build":
        # ML505Platform().build(tone, do_build=False, do_program=False).execute_local(run_script=False)
        ML505Platform().build(tone, do_program=False)
   