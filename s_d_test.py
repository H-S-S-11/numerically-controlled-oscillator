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
from fir_pipelined import FIR_Pipelined

from luna.gateware.interface.uart import UARTTransmitter


class Sigma_delta_test(Elaboratable):
    def __init__(self, k=15):
        self.k = k
        self.pdm_resolution = math.ceil(math.log2(k))

        self.pdm_o = Signal()
            
    def elaborate(self, platform):
        m = Module()

        m.submodules.pdm = self.pdm = pdm = PDM(resolution = self.pdm_resolution)
        m.submodules.adc = self.adc = adc = SigmaDelta_ADC(k=self.k)
        m.submodules.lpf = self.lpf = lpf = FIR_Pipelined(width=self.pdm_resolution+1,
            cutoff=1e3/100e6, taps=32)

        
    
        if(platform != None):
            platform.add_resources([
                Resource("pdm", 0,
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
                Resource("uart_tx", 0,
                    Pins("28", conn=("gpio", 0), dir ="o" ), 
                    Attrs(IOSTANDARD="LVCMOS33")
                ),
            ])
            self.pdm_o = platform.request("pdm")
            feedback = platform.request("feedback")
            comparator = platform.request("comparator")

        uart_tx = platform.request("uart_tx")
        uart_divisor = int(100e6/9600)
        m.submodules.uart = uart = UARTTransmitter(divisor=uart_divisor)
    
        m.d.comb += [
            adc.comparator.eq(comparator.i),
            feedback.o.eq(adc.feedback),
            lpf.input_ready_i.eq(1),
            lpf.input.eq(adc.output << 1),
            pdm.input.eq(lpf.output[0:self.pdm_resolution+1]),
            pdm.write_en.eq(0),
            self.pdm_o.o.eq(pdm.pdm_out), 

            uart.stream.valid.eq(Const(1)),
            uart.stream.first.eq(Const(1)),
            uart.stream.last .eq(Const(1)),
            # Use this one with four bit output to give single hex digit
            #uart.stream.payload.eq(lpf.output[0:self.pdm_resolution+1] + \
            #    Mux(lpf.output[3] &  (lpf.output[2] | lpf.output[1]), 55, 48) ),
            uart.stream.payload.eq(lpf.output[0:self.pdm_resolution+1] + 32),
            uart_tx.o.eq(uart.tx),
        ]       


        return m

if __name__ == "__main__":
  
    adc = Sigma_delta_test(k=64)
    
    ML505Platform().build(adc, do_program=False)
   