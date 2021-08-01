from nmigen import *
from nmigen.sim import *

class PDM(Elaboratable):
    def __init__(self, resolution):
        self.input = Signal(resolution)
        self.pdm_out = Signal(reset_less=True)
        self.write_en = Signal()
        self.resolution = resolution

    def elaborate(self, platform):
        m = Module()

        sum = Signal(self.resolution+1)
        accumulator = Signal(self.resolution, reset_less=True)
        input_reg = Signal(self.resolution)

        m.d.comb += [
            sum.eq(input_reg+accumulator),            
        ]

        m.d.sync += [
            accumulator.eq(sum[0:self.resolution]),
            self.pdm_out.eq(sum[self.resolution])
        ]

        with m.If(self.write_en):
            m.d.sync += input_reg.eq(self.input)
      
        return m

if __name__=="__main__":
    resolution = 4
    periods = 1
    dut = PDM(resolution)

    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz

    def clock():
        while True:
            yield
            #print("clock")

    def pulse_counter():
        pulse_count = 0
        clock_count = 0
        dut_input = 0
        old_input = 0
        pulses_since_change = 0
        while True:            
            if pulses_since_change == 2:
                output = (2**resolution)*pulse_count/clock_count
                print("input:", dut_input, "   pulses per "+str(2**resolution)+" clocks=", output)
                pulse_count = 0
                clock_count = 0              
            if (old_input != (yield dut.input)):
                #print("change")
                dut_input = old_input
                pulses_since_change = 0          
            old_input = yield dut.input
            yield
            if (yield dut.pdm_out)==1:
                pulse_count += 1
            clock_count += 1
            pulses_since_change += 1

    def input_val():
        count = 0        
        clocks = (2**resolution)*periods
        yield
        yield dut.write_en.eq(1)
        #yield dut.input.eq(4)
        #yield
        #yield dut.input.eq(1)
        #yield
        #yield
        for n in range(0, (2**resolution)):
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
        extra_time = periods*((2**resolution)**2)*10e-9
        print(extra_time)
        sim.run_until(1e-6+extra_time)
    
