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
from sigma_delta_adc import SigmaDelta_ADC

class Sigma_delta_test(Elaboratable):
    def __init__(self, k=15):
        self.k = k
        self.pwm_resolution = math.ceil(math.log2(k))

        self.pwm_o = Signal()
            
    def elaborate(self, platform):
        m = Module()

        m.submodules.pwm = self.pwm = pwm = PWM(resolution = self.pwm_resolution)
        m.submodules.adc = self.adc = adc = SigmaDelta_ADC(k=self.k)

        
    
        if(platform != None):
            platform.add_resources([
                Resource("pwm", 0,
                    Pins("48", conn=("gpio", 0), dir ="o" ), 
                    Attrs(IOSTANDARD="LVCMOS33")
                ),
                Resource("feedback", 0,
                    Pins("46", conn=("gpio", 0), dir ="o" ), 
                    Attrs(IOSTANDARD="LVCMOS33")
                ),
                Resource("comparator", 0,
                    DiffPairs("48", "46", conn=("gpio", 1), dir="i"),
                    Attrs(IOSTANDARD="LVDS_25")
                ),
            ])
            self.pwm_o = platform.request("pwm")
            feedback = platform.request("feedback")
            comparator = platform.request("comparator")

        # compare_out = Signal()
        # m.submodules.comparator_bufds = Instance("IBUFDS",
        #     i_I = comparator.p,
        #     i_IB= comparator.n,
        #     o_O = compare_out,
        # )

        m.d.comb += [
            adc.comparator.eq(comparator.i),
            feedback.o.eq(adc.feedback),
            pwm.input_value_i.eq(adc.output),
            pwm.write_enable_i.eq(0),
            self.pwm_o.o.eq(pwm.pwm_o),    
        ]       


        return m

if __name__ == "__main__":
  
    adc = Sigma_delta_test(k=16)
    
    ML505Platform().build(adc, do_program=False)
   