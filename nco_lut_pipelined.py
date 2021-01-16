from nmigen import *
from nmigen.sim import *
import math

def gen_lookup(entry, input_width, output_width, signed_output=True):
    #map the inputs to a normal phase
    phase = 2.0*math.pi*(entry/((2**input_width)-1))
    if signed_output:
        sin_phi = math.sin(phase)/2
    else:
        sin_phi = (math.sin(phase)+1)/2
    #map the output to a range of uints
    output = int((sin_phi)*((2**output_width)-1))
    return output

def calc_phi_inc(desired_freq, clock_freq):
    max_inc = (2**31)-1 #this would result in output frequency of fclk/2
    ratio = desired_freq/(clock_freq/2)
    return int(ratio*max_inc)

def twos_complement(decimal, bits):
    if(decimal >= 0):
        result =  bin(decimal)[2:]
        while len(result) < bits:
            result = "0" + result
        return result
    else:
        inverted = 2**bits + decimal
        return twos_complement(inverted, bits)

def generate_init_file(file, data_width, addr_width, signed_output = True):
    with open(file, "w") as mem_out:
        mem_out.write('memory_initialization_radix=2;'+'\n'+'memory_initialization_vector=\n')
        for n in range(0, 2**addr_width-1):
            decimal = gen_lookup(n, addr_width, data_width, signed_output=signed_output)
            bin_out = twos_complement(decimal, data_width)
            mem_out.write(bin_out + ',\n')
        decimal = gen_lookup(2**addr_width, addr_width, data_width, signed_output=signed_output)
        bin_out = twos_complement(decimal, data_width)
        mem_out.write(bin_out + ';')

def get_xilinx_bram(init_file, address, data_in, data_out, write_en, clk, rst):
    # 3 possible macros: SDP, TDP (simple/true dual port), SINGLE. start with single.
    bram = Instance("BRAM_SINGLE_MACRO", 
        p_BRAM_SIZE="18Kb",
        p_DEVICE="VIRTEX5",
        p_DO_REG = 1,
        p_INIT_FILE=init_file,
        p_WRITE_MODE="READ_FIRST",
        p_WRITE_WIDTH = 8,
        p_READ_WIDTH = 8,
        o_DO = data_out,
        i_ADDR = address,
        i_CLK = clk,
        i_DI = data_in,
        i_EN = 1,
        i_REGCE = 1,
        i_RST = rst,
        i_WE = write_en,
        )
    return bram

class NCO_LUT_Pipelined(Elaboratable):
    def __init__(self, output_width=8, sin_input_width=None, signed_output=True):
        self.phi_inc_i = Signal(31)

        self.signed_output = signed_output
        if (signed_output):
            self.sine_wave_o = Signal(shape=signed(output_width))
        else:
            self.sine_wave_o = Signal(shape=unsigned(output_width))
        
        self.output_width = output_width
        if sin_input_width:
            self.sin_input_width = sin_input_width
        else:
            self.sin_input_width = output_width

    def elaborate(self, platform):
        m = Module()

          

        sin_o = self.sine_wave_o
        input_width = self.sin_input_width
        output_width = self.output_width

        phi = Signal(32)
        m.d.sync += phi.eq(phi + self.phi_inc_i)

        table_entry = Signal(input_width)
        m.d.comb += table_entry.eq(phi[32-input_width:32])

        #generate_init_file("./build/mem_init.mem", 10, 10)
        bram = get_xilinx_bram("mem_init.mem", table_entry, Signal(10), sin_o, Signal(2), ClockSignal(), ResetSignal())
        m.submodules += bram

        return m

if __name__ == "__main__":

    dut = NCO_LUT_Pipelined(signed_output=True)
    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz

    def clock():
        while True:
            yield

    def input_freq():
        phi_inc = calc_phi_inc(9000000, 100000000) #9MHz
        yield dut.phi_inc_i.eq(phi_inc)

    sim.add_sync_process(clock)
    sim.add_sync_process(input_freq)

    with sim.write_vcd("NCO_LUT_waves.vcd"):
        sim.run_until(1e-5)