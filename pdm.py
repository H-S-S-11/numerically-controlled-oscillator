from nmigen import *
from nmigen.sim import *

class PDM(Elaboratable):
    def __init__(self, bitwidth):
        self.input = Signal(bitwidth)
        self.pdm_out = Signal()
        self.write_en = Signal()
        self.bitwidth = bitwidth

    def elaborate(self, platform):
        m = Module()

        sum = Signal(self.bitwidth+1)
        accumulator = Signal(self.bitwidth, reset_less=True)
        input_reg = Signal(self.bitwidth)

        m.d.sync += [
            accumulator.eq(sum[0:self.bitwidth]),
        ]

        with m.If(self.write_en):
            m.d.sync += input_reg.eq(self.input)

        m.d.comb += [
            sum.eq(input_reg+accumulator),
            self.pdm_out.eq(sum[self.bitwidth])
        ]

        return m

if __name__=="__main__":
    bitwidth = 7
    periods = 1
    dut = PDM(bitwidth)

    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz

    def clock():
        while True:
            yield

    def pulse_counter():
        pulse_count = 0
        clock_count = 0
        dut_input = 0
        old_input = 0
        while True:            
            if (old_input != (yield dut.input)):
                output = (2**bitwidth)*pulse_count/clock_count
                print("input:", old_input, "   pulses per "+str(2**bitwidth)+" clocks=", output)
                pulse_count = 0
                clock_count = 0
            old_input = yield dut.input
            yield
            if (yield dut.pdm_out)==1:
                pulse_count += 1
            clock_count += 1

    def input_val():
        count = 0        
        clocks = (2**bitwidth)*periods
        yield
        yield dut.write_en.eq(1)
        #yield dut.input.eq(4)
        #yield
        #yield dut.input.eq(1)
        #yield
        #yield
        for n in range(0, (2**bitwidth)):
            yield dut.input.eq(n)
            for clk in range(0, clocks):
                yield
        yield dut.input.eq(0)
        yield
        yield
        #for n in range(0, 8):
        #    yield dut.input.eq(n)
        #    for clk in range(0, clocks):
        #        yield

    sim.add_sync_process(clock)
    sim.add_sync_process(input_val)
    sim.add_sync_process(pulse_counter)

    with sim.write_vcd("PDM_waves.vcd"):
        extra_time = periods*((2**bitwidth)**2)*10e-9
        print(extra_time)
        sim.run_until(1e-5+extra_time)
    
