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
from pwm import *
from fir_pipelined import *
from ac97_controller import AC97_Controller

class Tone_synth_loopback(Elaboratable):
    def __init__(self, tone_frequency=440, clk_frequency=100000000, resolution = 6, pwm_resolution=None):
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
        m.submodules.ac97 = self.ac97 = ac97 = AC97_Controller()
        m.submodules.pwm = self.pwm = pwm = PWM(resolution = self.pwm_resolution)
        m.submodules.fir = fir = FIR_Pipelined(width=16, taps=17, cutoff=0.45, #10kHz Hz at 44k Fs
            filter_type='highpass', macc_width=48)
    
        if(platform != None):

            platform.add_resources([
                Resource("pwm", 0,
                    Pins("2", conn=("gpio", 0), dir ="o" ), 
                    Attrs(IOSTANDARD="LVCMOS33")
                    ),
            ])
            self.pwm_o = platform.request("pwm")

            #Get the clock from the codec
            m.domains.audio_bit_clk = ClockDomain()
            audio_clk = platform.request("audio_bit_clk")
            m.d.comb += ClockSignal("audio_bit_clk").eq(audio_clk)
            
            #request the AC97 interface signals, with DDR for the input
            ac97_if = platform.request("audio_codec", 
                xdr={"sdata_in":2, "sdata_out":0, "audio_sync":0, "reset_o":0})
            ac97_if.sdata_in.i_clk = audio_clk
            ac97.sdata_in = ac97_if.sdata_in
            ac97.sdata_out = ac97_if.sdata_out
            ac97.sync_o = ac97_if.audio_sync
            ac97.reset_o = ac97_if.flash_audio_reset_b
  
        m.d.comb += [
            nco.phi_inc_i.eq(self.phi_inc),
            pwm.input_value_i.eq(nco.sine_wave_o),
            pwm.write_enable_i.eq(0),
            #ac97.dac_channels_i.dac_left_front.eq(ac97.adc_channels_o.adc_left),
            #ac97.dac_channels_i.dac_right_front.eq(ac97.adc_channels_o.adc_right),
            fir.input.eq(ac97.adc_channels_o.adc_left[4:20]),
            fir.input_ready_i.eq(ac97.adc_sample_received),
            ac97.dac_channels_i.dac_left_front.eq(fir.output),
            ac97.dac_channels_i.dac_right_front.eq(fir.output),
            self.pwm_o.o.eq(pwm.pwm_o),     
        ]

        return m

if __name__ == "__main__":
  
    tone = Tone_synth_loopback(resolution = 6, clk_frequency=100000000)

    if sys.argv[1] == "convert":
        path = "tone_synth_outputs"
        if not os.path.exists(path):
            os.makedirs(path)    
        out = open("tone_synth_outputs/tone_synth.v", "w")
        out.write(convert(tone, ports=[tone.pwm_o.o]))

    elif sys.argv[1] == "build":
        ML505Platform().build(tone, do_build=False, do_program=False).execute_local(run_script=False)
    
   