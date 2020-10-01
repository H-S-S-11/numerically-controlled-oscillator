from nmigen import *
from nmigen.back.pysim import *

from nco_lut import *
from pwm import PWM

class tone_synth(Elaboratable):
    def __init__(self, tone_frequency=440, clk_frequency=50000000):
        self.pwm_o = Signal()

        self.phi_inc = calc_phi_inc(tone_frequency, clk_frequency)
    
    def elaborate(self, platform):
        m = Module()

        m.submodules.nco = self.nco = nco = NCO_LUT()
        m.submodules.pwm = self.pwm = pwm = PWM()

        m.d.comb += [
            nco.phi_inc_i.eq(self.phi_inc),
            pwm.input_value_i.eq(nco.sine_wave_o),
            pwm.write_enable_i.eq(0),
            self.pwm_o.eq(pwm.pwm_o),
        ]


        return m

if __name__ == "__main__":
    