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
        coefficients = Memory(width=self.width, depth=self.taps, init=self.coefficients)
        samples = Array(iterable=Signal(shape=self.sample, reset_less=True))
        accumulator = Signal(shape = Shape(width=32, signed=True))

        m.d.sync += [
            self.output_ready_o.eq(0),
            accumulator.eq(samples[sample_count]*coefficients[sample_count] ),
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
                    self.output.eq(accumulator[(31-self.width):31]),
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

    def tb():
        yield dut.input.eq(0)
        yield
        yield dut.input_ready_i.eq(1)
        yield
        yield dut.input_ready_i.eq(0)
        yield from wait_output_ready()
        yield dut.input_ready_i.eq(1)
        yield
        yield dut.input_ready_i.eq(0)

    sim.add_sync_process(clock)
    sim.add_sync_process(tb)

    with sim.write_vcd("fir_waves.vcd"):
        sim.run_until(1e-6, run_passive=True)
