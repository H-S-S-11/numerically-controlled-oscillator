import os
import sys
from nmigen import *
from nmigen.hdl.rec import *
from nmigen.back.pysim import *
from nmigen.back.verilog import *
from nmigen.build import *
from nmigen.build.res import *
from nmigen.lib.io import Pin
from nmigen.hdl.ir import Instance
from nmigen_boards.de4 import DE4Platform
from nmigen_boards.de10_nano import DE10NanoPlatform

from nco_lut import *
from pwm import PWM

class Blank():
    pass

def inst_pll(pll_file_name, domain, pll_module_name, freq, platform, m):
    ret = Blank()
    ret.pll_clk = Signal()
    ret.locked = Signal()

    m.domains += ClockDomain(domain)
    m.d.comb += ClockSignal(domain=domain).eq(ret.pll_clk)

    with open(pll_file_name) as f:
        platform.add_file(pll_file_name, f)

    setattr(m.submodules, domain,
        Instance \
        (
            pll_module_name,

            i_inclk0=platform.request("clk50", 1, dir="-"),
            o_c0=ret.pll_clk,
        ))

    platform.add_clock_constraint(ret.pll_clk, freq)

    return ret

class Tone_synth(Elaboratable):
    def __init__(self, tone_frequency=440, clk_frequency=600000000, resolution = 8, pwm_resolution=None):
        self.pwm_o = Pin(1, "o")

        self.phi_inc = calc_phi_inc(tone_frequency, clk_frequency)

        self.resolution = resolution
        if pwm_resolution==None:
            self.pwm_resolution = resolution
        else:
            self.pwm_resolution = pwm_resolution

    def __elab_build_pll200(self, m):
        return inst_pll("C:/intelFPGA/18.0/SIV_pll_600M/SIV_pll_600M.v", "clk600", "SIV_pll_600M", 600000000, self.platform, m)
            
    def elaborate(self, platform):
        self.platform = platform
        m = Module()

        pll200 = self.__elab_build_pll200(m)

        m.submodules.nco = self.nco = nco \
            = DomainRenamer({"sync": "clk600"})(NCO_LUT(output_width= self.pwm_resolution, sin_input_width=self.resolution))
        m.submodules.pwm = self.pwm = pwm \
            = DomainRenamer({"sync": "clk600"})(PWM(resolution = self.pwm_resolution))
    
    
        platform.add_resources([
            Resource("pwm", 0,
                Pins("1", conn=("gpio", 0), dir ="o" ), 
                Attrs(io_standard="3.0-V PCI")
                ),
        ])
        
        self.pwm_o = platform.request("pwm")

        m.d.comb += [
            nco.phi_inc_i.eq(self.phi_inc),
            pwm.input_value_i.eq(nco.sine_wave_o),
            pwm.write_enable_i.eq(0),
            self.pwm_o.o.eq(pwm.pwm_o),
        ]
       

        return m

if __name__ == "__main__":
  
    tone = Tone_synth(resolution = 6, pwm_resolution=6)

    if sys.argv[1] == "convert":
        path = "tone_synth_outputs"
        if not os.path.exists(path):
            os.makedirs(path)    
        out = open("tone_synth_outputs/tone_synth.v", "w")
        out.write(convert(tone, ports=[tone.pwm_o.o]))

    elif sys.argv[1] == "build":
        DE4Platform().build(tone, do_program=False)
    elif sys.argv[1] == "program":
        DE4Platform().build(tone, do_program=True)
   