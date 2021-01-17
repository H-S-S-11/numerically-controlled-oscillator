from nmigen import *
from nmigen.build import *
from nmigen.build.res import *
from nmigen.lib.io import Pin
from nmigen_boards.ml505 import ML505Platform
from nmigen_boards.test.blinky import *
import itertools

def get_xilinx_RAMB16(init_file, address, data_in, data_out, write_en, clk, rst):
    # 3 possible macros: SDP, TDP (simple/true dual port), SINGLE. start with single.
    bram = Instance("RAMB18SDP", 
        p_DO_REG = 0,
        p_INIT_FILE=init_file,
        o_DO = data_out,
        i_WRADDR = address,
        i_RDADDR = address,
        i_WRCLK = clk,
        i_RDCLK = clk,
        i_DI = data_in,
        i_RDEN = Signal(1, reset=1),
        i_WREN = 0,
        i_REGCE = Signal(1, reset=1),
        i_SSR = 0,
        i_WE = write_en,
        )
    return bram

class BRAMWrapper(Elaboratable):
    def __init__(self):
        self.read_port = Signal(32)
        self.address = Signal(9)
    def elaborate(self, platform):
        m = Module()
        bram_prim = get_xilinx_RAMB16("mem_init.mem", self.address, Signal(32), self.read_port, Signal(4), ClockSignal(), ResetSignal())
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

        bram = BRAMWrapper(name="bram0")
        m.submodules += bram
        m.d.comb += bram.address.eq(Cat(switches, Signal(1)))

        m.d.sync += [
            Cat(led[0], led[1]).eq(bram.read_port[0:2]),
            led[2].eq(switches[0]),
        ]

        return m

bram_test = BRAMTest()
ML505Platform().build(bram_test, do_build=False, do_program=False).execute_local(run_script=False)