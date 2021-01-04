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
from ac97_controller import AC97_Controller

class Tone_synth(Elaboratable):
    def __init__(self, tone_frequency=440, clk_frequency=100000000, resolution = 10, pwm_resolution=None):
        self.pwm_o = Pin(1, "o")

        self.phi_inc = calc_phi_inc(tone_frequency, clk_frequency)
        self.phi_inc_2 = calc_phi_inc(tone_frequency/2, clk_frequency)

        self.resolution = resolution
        if pwm_resolution==None:
            self.pwm_resolution = resolution
        else:
            self.pwm_resolution = pwm_resolution
            
    def elaborate(self, platform):
        m = Module()

        m.submodules.nco_1 = self.nco_1 = nco_1 = NCO_LUT(output_width=self.pwm_resolution, 
            sin_input_width=self.resolution)
        m.submodules.nco_2 = self.nco_2 = nco_2 = NCO_LUT(output_width=self.pwm_resolution, 
            sin_input_width=self.resolution, signed_output=False)
        m.submodules.ac97 = self.ac97 = ac97 = AC97_Controller()
    
        if(platform != None):
            
            ac97_if = platform.request("audio_codec", 
                xdr={"sdata_in":2, "sdata_out":0, "audio_sync":0, "reset_o":0})
            ac97.sdata_in = ac97_if.sdata_in
            ac97.sdata_out = ac97_if.sdata_out
            ac97.sync_o = ac97_if.audio_sync
            ac97.reset_o = ac97_if.flash_audio_reset_b

            #Get the clock from the codec
            m.domains.audio_bit_clk = ClockDomain()
            audio_clk = platform.request("audio_bit_clk")
            m.d.comb += ClockSignal("audio_bit_clk").eq(audio_clk)
            
        zero=Signal(10)
        m.d.comb += [
            nco_1.phi_inc_i.eq(self.phi_inc_2),
            nco_2.phi_inc_i.eq(self.phi_inc_2),
            ac97.dac_channels_i.dac_left_front.eq(Cat(zero, nco_1.sine_wave_o)),
            ac97.dac_channels_i.dac_right_front.eq(Cat(zero, nco_2.sine_wave_o)),
        ]

        return m

if __name__ == "__main__":
  
    tone = Tone_synth(resolution = 10, clk_frequency=100000000)

    if sys.argv[1] == "convert":
        path = "tone_synth_outputs"
        if not os.path.exists(path):
            os.makedirs(path)    
        out = open("tone_synth_outputs/tone_synth.v", "w")
        out.write(convert(tone, ports=[tone.pwm_o.o]))

    elif sys.argv[1] == "build":
        ML505Platform().build(tone, do_build=False, do_program=False).execute_local(run_script=False)
    
   