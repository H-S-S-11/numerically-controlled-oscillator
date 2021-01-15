from nmigen import *
from nmigen.sim import *
#import numpy
import math

class FIR_Pipelined(Elaboratable):
    def __init__(self, width = 16, coefficients={0.1, 0.2}):
        #self.coefficients = coefficients #here do conversion from float to int
        self.coefficients = {   #10kHz LPF at 44kHz-ish sampling rate
            -81, -134, 318, 645, -1257, -2262, 4522, 14633, 
            14633, 4522, -2262, -1257, 645, 318, -134, -81
        }

        self.sample = Shape(width=width, signed=True)
        self.taps = math.ceil(math.log2(len(self.coefficients)))

        self.input = Signal(shape = self.sample) 
        self.input_ready_i = Signal()
        self.output = Signal(shape = self.sample) 
        self.output_ready = Signal()        

    def elaborate(self, platform):
        m = Module()

        sample_count = 


        return m


if __name__=="__main__":
    #from scipy import signal
    import math