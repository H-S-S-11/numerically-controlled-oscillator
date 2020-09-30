from nmigen import *
from nmigen.back.pysim import *

class PWM(Elaboratable):
    def __init__(self, resolution = 8):
        self.input_value_i = Signal(resolution)
        self.write_enable_i = Signal()
        self.pwm_o = Signal(reset = 1)

        self.resolution = resolution

    def elaborate(self, platform):
        m = Module()

        count = Signal(self.resolution)
        input_value = Signal(self.resolution)
        m.d.sync += count.eq(count + 1)

        with m.If(self.write_enable_i):
            m.d.sync += input_value.eq(self.input_value_i)

        with m.If(count == self.input_value_i):
            m.d.sync += self.pwm_o.eq(0)
        with m.Else():
            with m.If(count.all()):
                m.d.sync += [
                    self.pwm_o.eq(1),
                    input_value.eq(self.input_value_i),
                ]


        return m

if __name__ == "__main__":

    dut = PWM(8)
    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz

    def clock():
        while True:
            yield

    def input_val():
        yield dut.input_value_i.eq(100)
        yield dut.write_enable_i.eq(0)

    sim.add_sync_process(clock)
    sim.add_sync_process(input_val)

    with sim.write_vcd("PWM_waves.vcd"):
        sim.run_until(5e-5)
    