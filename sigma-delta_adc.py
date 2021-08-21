from sys import maxsize
from nmigen import *
from nmigen.sim import *
import math

class SigmaDelta_ADC(Elaboratable):
    def __init__(self, k=8):
        self.comparator = Signal()
        self.feedback = Signal()
        self.output = Signal( math.ceil(math.log2(k)) )

        

        self.k = k

    def elaborate(self, platform):
        m = Module()

        counter = Signal(shape=range(self.k))
        shift_in = Signal(self.k)

        m.d.sync += [
            self.feedback.eq(self.comparator),
            counter.eq(counter+1),
            shift_in.eq(Cat(self.comparator, shift_in)),
        ]

        return m

if __name__=="__main__":
    dut = SigmaDelta_ADC()

    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz

    def clock():
        while True:
            yield
    
    def circuit():
        integrator = 0.5
        input = 0.8
        while True:
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
        sim.run_until(1e-6)