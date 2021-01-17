from nmigen import *
from nmigen.build import *
from nmigen.build.res import *
from nmigen.lib.io import Pin
from nmigen_boards.ml505 import ML505Platform
from nmigen_boards.test.blinky import *
import itertools

def get_xilinx_RAMB16(init_file, address, data_in, data_out, write_en, clk, rst, init_data):
    # 3 possible macros: SDP, TDP (simple/true dual port), SINGLE. start with single.
    bram = Instance("RAMB18SDP", 
        p_DO_REG = 1,
        #   each INIT_xx paramater represents a block of 8 words
        #   (BRAM is 32 bits wide without parity)
        #   MSB first in the parameter
        **init_data,
        o_DO = data_out,              
        i_WRADDR = address,
        i_RDADDR = address,
        i_WRCLK = clk,
        i_RDCLK = clk,
        i_DI = data_in,
        i_RDEN = Const(1, unsigned(1)),
        i_WREN = Const(0, unsigned(1)),
        i_REGCE = Const(1, unsigned(1)),
        i_SSR = Const(0, unsigned(1)),
        i_WE = write_en,
        )
    return bram

#   leftover from BMM experiments. consider deleting
class BRAMWrapper(Elaboratable):
    def __init__(self):
        self.read_port = Signal(32)
        self.address = Signal(9)
    def elaborate(self, platform):
        m = Module()
        init = { 'p_INIT_00':Const(10, unsigned(256)) }
        bram_prim = get_xilinx_RAMB16("mem_init.mem", self.address, Const(0, unsigned(32)),
            self.read_port, Const(0, unsigned(4)), ClockSignal(), ResetSignal(), init)
        m.submodules += bram_prim
        return m

class BRAMTest(Elaboratable):
    def __init__(self):
        pass


    def elaborate(self, platform):

        def get_all_resources(name):
            resources = []
            for number in itertools.count():
                try:
                    resources.append(platform.request(name, number))
                except ResourceError:
                    break
            return resources

        m=Module()

        led     = [res.o for res in get_all_resources("led")]
        switches = [res.i for res in get_all_resources("switch")]
       
        bram = BRAMWrapper()
        m.submodules.bram = bram

        m.d.comb += [
            bram.address.eq( Cat(switches, Const(0, unsigned(1))) ),
            Cat(led[0], led[1]).eq(bram.read_port[0:2]),
            led[2].eq(switches[0]),
        ]

        return m

bram_test = BRAMTest()
ML505Platform().build(bram_test, do_build=False, do_program=False).execute_local(run_script=False)