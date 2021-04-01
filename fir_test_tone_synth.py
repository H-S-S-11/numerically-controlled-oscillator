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
from fir_pipelined import *
from pwm import PWM
from peripherals.ac97 import *

class FIR_test(Elaboratable):
    def __init__(self, tone_frequency=440, clk_frequency=100000000, resolution = 8, pwm_resolution=None):
        self.pwm_o = Pin(1, "o")

        self.phi_inc = calc_phi_inc(tone_frequency, clk_frequency)

        self.resolution = resolution
        if pwm_resolution==None:
            self.pwm_resolution = resolution
        else:
            self.pwm_resolution = pwm_resolution
            
    def elaborate(self, platform):
        m = Module()

        m.submodules.nco = self.nco = nco = NCO_LUT(output_width= 6, 
            sin_input_width=6, signed_output=True)
        m.submodules.nco2 = nco2 = NCO_LUT(output_width= 6, 
            sin_input_width=6, signed_output=True)
        m.submodules.pwm = self.pwm = pwm = PWM(resolution = self.pwm_resolution)
        m.submodules.fir = fir = FIR_Pipelined(width=7, taps = 23, cutoff=0.45, #10kHz at 44k Fs
            filter_type='lowpass', macc_width=32, output_width=7)
        m.submodules.ac97 = self.ac97 = ac97 = AC97_Controller()
        

        div_2000 = Signal(range(0, 2000))
        sample = Signal()
        pwm_val = Signal(8)
        m.d.comb += [
            sample.eq(0),
            pwm_val.eq(fir.output + 128),
            #pwm_val.eq(nco.sine_wave_o + (nco2.sine_wave_o >> 1) + 128),
        ]
        m.d.sync += div_2000.eq(div_2000-1)
        with m.If(~div_2000.any()):
            m.d.comb += sample.eq(1)
            m.d.sync += div_2000.eq(1999)    
    
        if(platform != None):
            platform.add_resources([
                Resource("pwm", 0,
                    Pins("2", conn=("gpio", 0), dir ="o" ), 
                    Attrs(IOSTANDARD="LVCMOS33")
                    ),
            ])
            self.pwm_o = platform.request("pwm")

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

        zero = Signal(11)
        m.d.comb += [
            nco.phi_inc_i.eq(self.phi_inc),
            nco2.phi_inc_i.eq(self.phi_inc*8),
            fir.input.eq(nco.sine_wave_o + nco2.sine_wave_o),
            fir.input_ready_i.eq(ac97.adc_sample_received),
            ac97.dac_channels_i.dac_left_front.eq(Cat(zero, fir.output)),
            ac97.dac_channels_i.dac_right_front.eq(Cat(zero, fir.output)),
            pwm.input_value_i.eq(pwm_val),
            pwm.write_enable_i.eq(0),
            self.pwm_o.o.eq(pwm.pwm_o),
        ]

        return m

if __name__ == "__main__":
  
    tone = FIR_test(resolution = 16, pwm_resolution=8, 
        tone_frequency=440, clk_frequency=100000000)

    if sys.argv[1] == "convert":
        path = "tone_synth_outputs"
        if not os.path.exists(path):
            os.makedirs(path)    
        out = open("tone_synth_outputs/tone_synth.v", "w")
        out.write(convert(tone, ports=[tone.pwm_o.o]))

    elif sys.argv[1] == "build":
        ML505Platform().build(tone, do_build=True, do_program=False)

    elif sys.argv[1] == "sim":
        sim = Simulator(tone)
        sim.add_clock(10e-9) #100MHz
        sim.add_clock(81e-9, domain="audio_bit_clk")

        def clock():
            while True:
                yield

        def adc_input():
            for n in range(0, 56):
                yield
            while True:
                yield tone.ac97.sdata_in.i1.eq(1)
                yield
                yield tone.ac97.sdata_in.i1.eq(0)
                yield

        sim.add_sync_process(clock)
        sim.add_sync_process(clock, domain="audio_bit_clk")
        sim.add_sync_process(adc_input, domain="audio_bit_clk")
        

        with sim.write_vcd("ac97_fir_waves.vcd"):
            sim.run_until(1e-3, run_passive=True)
    
   