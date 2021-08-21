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
        shift_in = Signal(self.k)
        adder_chain = [Signal(self.k, name="input_buffer")]
        valid = Signal(int(math.log2(self.k))+1)

        m.d.sync += [
            self.feedback.eq(self.comparator),
            counter.eq(counter+1),
            shift_in.eq(Cat(self.comparator, shift_in)),
            valid.eq(Cat(0, valid))
        ]

        with m.If(counter==0):
            m.d.sync += [
                adder_chain[0].eq(shift_in),
                valid.eq(1),
            ]

        for i in range(1, int(math.log2(self.k)+1)):
            adder_chain.append([])
            for n in range(0, int(self.k/(2**i))):
                adder_chain[i].append( Signal(1+i, name="adder_chain_"+str(i-1)+"_"+str(n)) )
                m.d.sync += adder_chain[i][n].eq(adder_chain[i-1][2*n]+adder_chain[i-1][2*n+1])
        
        m.d.comb += [
            self.output.eq(adder_chain[int(math.log2(self.k))][0]),
            self.new_output.eq(valid[int(math.log2(self.k))]),
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
            input = 0.5*(math.sin(2*math.pi*f*(t/100e6))+1)
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