from nmigen import *
from nmigen.sim import *
#import numpy
import math

class FIR_Pipelined(Elaboratable):
    def __init__(self, width = 16, coefficients=None):
        self.coefficients = [   #LPF at approximately half of nyquist rate, eg 10kHz at 40kHz sample rate
            -81, -134, 318, 645, -1257, -2262, 4522, 14633, 
            14633, 4522, -2262, -1257, 645, 318, -134, -81
        ]
        if (coefficients != None):
            pass
            #self.coefficients = coefficients #here do conversion from float to int

        self.width = width
        self.sample = Shape(width=self.width, signed=True)
        self.taps = len(self.coefficients)

        self.input = Signal(shape = self.sample) 
        self.input_ready_i = Signal()
        self.output = Signal(shape = self.sample) 
        self.output_ready_o = Signal()        

    def elaborate(self, platform):
        m = Module()

        sample_count = Signal(math.ceil(math.log2(self.taps)))
        accumulator = Signal(shape = Shape(width=32, signed=True))
        multiply_result = Signal(shape = Shape(width=32, signed=True))

        multiplicand1 = Signal(shape = self.sample) 
        multiplicand2 = Signal(shape = self.sample) 

        coefficients = Memory(width=self.width, depth=self.taps, 
            init=self.coefficients, name="coefficients")
        samples = Memory(width=self.width, depth=self.taps, 
            name = "samples")

        m.d.comb += [
            multiply_result.eq(multiplicand1*multiplicand2),
            multiplicand1.eq(samples[sample_count]),
            multiplicand2.eq(coefficients[sample_count]),
        ]

        m.d.sync += [
            self.output_ready_o.eq(0),
            accumulator.eq(accumulator + multiply_result),
        ]

        with m.FSM() as fir_fsm:
            with m.State("WAIT"):
                m.next = "WAIT"
                m.d.sync += accumulator.eq(0)
                with m.If(self.input_ready_i):
                    m.next = "LOAD"

            with m.State("LOAD"):
                m.next = "PROCESSING"
                for i in range(1, self.taps):
                        m.d.sync += samples[i].eq(samples[i-1])
                m.d.sync += [
                    accumulator.eq(0),
                    samples[0].eq(self.input),                    
                ]

            with m.State("PROCESSING"):
                m.next = "PROCESSING"
                m.d.sync += sample_count.eq(sample_count+1) 
                with m.If(sample_count==(self.taps-1)):
                    m.d.sync += sample_count.eq(0)
                    m.next = "SAVE"

            with m.State("SAVE"):
                m.next = "WAIT"
                m.d.sync += [
                    self.output_ready_o.eq(1),
                    self.output.eq(accumulator[(32-self.width):32]),
                ]

        return m


if __name__=="__main__":
    #from scipy import signal
    import math

    dut = FIR_Pipelined()
    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz

    def clock():
        while True:
            yield

    def wait_output_ready():
        while (not (yield dut.output_ready_o)):
            yield

    def signal(t):
        # frequency is (w/2*pi)*2 MHz
        # max w is pi. (represents nyquist rate)
        w1 = 3.14159
        return (math.sin(w1*t) )/2

    def tb():
        yield dut.input.eq(0)
        yield
        for t in range(0,100):      #100 samples with a 50 clock cycle sampling period 
            yield dut.input_ready_i.eq(1)    # (500ns, 2MHz sample rate. default filter has 500kHz cutoff)            
            yield dut.input.eq(round(signal(t)*(2**15)))
            yield
            yield dut.input_ready_i.eq(0)
            for n in range(0, 49):
                yield
        

    sim.add_sync_process(clock)
    sim.add_sync_process(tb)

    with sim.write_vcd("fir_waves.vcd"):
        sim.run_until(5e-5, run_passive=True)
