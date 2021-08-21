from sys import maxsize
from nmigen import *
from nmigen.sim import *
import math

class SigmaDelta_ADC(Elaboratable):
    def __init__(self, k=16):
        if (k<=1) or (math.ceil(math.log2(k)) != math.log2(k)):
            raise ValueError("k must be a power of 2 greater than 1")

        self.comparator = Signal()
        self.feedback = Signal()
        self.output = Signal( 1 + math.ceil(math.log2(k)) )
        self.new_output = Signal()
        
        
        self.k = k

    def elaborate(self, platform):
        m = Module()

        counter = Signal(shape=range(self.k))
        accumulator = Signal(shape=self.output.shape())
        
        m.d.sync += [
            self.feedback.eq(self.comparator),
            counter.eq(counter+1),
            accumulator.eq(self.comparator + accumulator),
            self.new_output.eq(0)
        ]

        with m.If(counter==0):
            m.d.sync += [
                accumulator.eq(self.comparator),
                self.output.eq(accumulator),
                self.new_output.eq(1),
            ]
 

        return m

if __name__=="__main__":
    k = 32
    dut = SigmaDelta_ADC(k=k)

    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz

    def clock():
        while True:
            yield
    
    def circuit():
        integrator = 0.5
        input = 0.4
        f = 5e4
        t = 0
        yield dut.output.eq(k) # Drive high at the start to set gtkwave range
        yield
        while True:
            #input = 0.5*(math.sin(2*math.pi*f*(t/100e6))+1)
            t += 1
            fb = yield dut.feedback
            if fb==1:
                integrator += 0.05*(1-integrator)
            else:
                integrator = integrator - 0.05*integrator
            yield dut.comparator.eq(input>integrator)
            # print(integrator)
            yield

    sim.add_sync_process(clock)
    sim.add_sync_process(circuit)

    with sim.write_vcd("S-D_ADC_waves.vcd"):
        sim.run_until(5e-5)