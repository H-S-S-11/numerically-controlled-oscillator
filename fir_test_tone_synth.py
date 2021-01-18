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

        m.submodules.nco = self.nco = nco = NCO_LUT(output_width= self.resolution, 
            sin_input_width=8, signed_output=True)
        m.submodules.pwm = self.pwm = pwm = PWM(resolution = self.pwm_resolution)
        m.submodules.fir = fir = FIR_Pipelined(width=16, taps = 17, cutoff=0.2, #5kHz at 50k Fs
            filter_type='lowpass', macc_width=48)

        div_2000 = Signal(range(0, 2000))
        sample = Signal()
        pwm_val = Signal(8)
        m.d.comb += [
            sample.eq(0),
            pwm_val.eq(fir.output[8:16] + 128),
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

        m.d.comb += [
            nco.phi_inc_i.eq(self.phi_inc),
            fir.input.eq(nco.sine_wave_o),
            fir.input_ready_i.eq(sample),
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
        ML505Platform().build(tone, do_build=False, do_program=False).execute_local(run_script=False)

    elif sys.argv[1] == "sim":
        sim = Simulator(tone)
        sim.add_clock(10e-9) #100MHz
        def clock():
            while True:
                yield
        sim.add_sync_process(clock)
        

        with sim.write_vcd("pwm_fir_waves.vcd"):
            sim.run_until(5e-4, run_passive=True)
    
   