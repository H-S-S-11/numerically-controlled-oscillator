from nmigen import *
from nmigen.sim import *
from nmigen.lib.cdc import *

# AC97 is a 16 bit "Tag" followed by 12 20-bit data backets,
# with the interface written to on rising edges of bit_clk,
# and sampled on the falling edge

class AC97_Controller(Elaboratable):
    def __init__(self):
        #AC97 signals
        self.sdata_in = Signal()
        self.sdata_out = Signal()
        self.sync_o = Signal()
        self.reset_o = Signal()

        # pcm inputs to dac
        self.dac_tag_i = Signal(6)                #Indicates which slots are valid
        self.dac_left_front_i = Signal(20)        # slot 3
        self.dac_right_front_i = Signal(20)       # slot 4
        self.dac_centre_i = Signal(20)            # slot 6
        self.dac_left_surround_i = Signal(20)     # slot 7
        self.dac_right_surround_i = Signal(20)    # slot 8
        self.dac_lfe_i = Signal(20)               # slot 9
        self.dac_sample_written = Signal()        # asserted for one cycle when inputs sampled
        

        # pcm outputs from adc
        self.adc_tag = Signal(3)                #Indicates which slots are valid
        self.adc_left = Signal(20)              # slot 3
        self.adc_right = Signal(20)             # slot 4
        self.adc_mic = Signal(20)               # slot 6
        

    def elaborate(self, platform):
        m = Module()

        self.bit_clk = bit_clk = ClockDomain()
        bit_clk_n = ClockDomain(clk_edge="neg")

        dac_inputs_valid = Signal()
        dac_valid_ack_sync = Signal()
        
        #input buffers
        dac_tag = Signal(6)      
        dac_left_front = Signal(20)        
        dac_right_front = Signal(20)    
        dac_centre = Signal(20)            
        dac_left_surround = Signal(20)     
        dac_right_surround = Signal(20)    
        dac_lfe = Signal(20)               

        with m.If (~dac_inputs_valid & ~dac_valid_ack_sync):    
            m.d.sync += [
                dac_inputs_valid.eq(1),
                dac_tag.eq(self.dac_tag_i),
                dac_left_front.eq(self.dac_left_front_i),
            ]

        with m.If (dac_inputs_valid & dac_valid_ack_sync):
            m.d.comb += self.dac_sample_written.eq(1)
            m.d.sync += dac_inputs_valid.eq(0)

        #bit_clk domain
        dac_valid_ack = Signal()
        dac_inputs_valid_sync = Signal()
        m.submodules.dac_input_valid_2ff = dac_input_valid_2ff = FFSynchronizer(dac_inputs_valid,
            dac_inputs_valid_sync, o_domain="bit_clk")
        m.submodules.dac_ack_2ff = dac_ack_2ff = FFSynchronizer(dac_valid_ack,
            dac_valid_ack_sync, o_domain="sync")
        dac_tag_sync = Signal(6)      
        dac_left_front_sync = Signal(20)        

        with m.If(~dac_valid_ack & dac_inputs_valid_sync):
            m.d.bit_clk += [
                dac_valid_ack.eq(1),
                dac_tag_sync.eq(dac_tag),
                dac_left_front_sync.eq(dac_left_front)        
        ]

        with m.If(dac_valid_ack & ~dac_inputs_valid_sync):
            m.d.bit_clk += dac_valid_ack.eq(0)

        #bit_clk_n domain
        adc_outputs_valid = Signal()
        adc_valid_ack = Signal()
        m.d.bit_clk_n += adc_valid_ack.eq(0)


        return m


if __name__=="__main__":

    dut = AC97_Controller()
    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz
    sim.add_clock(81e-9, domain="bit_clk")
    sim.add_clock(81e-9, domain="bit_clk_n")

    def clock():
        while True:
            yield

    sim.add_sync_process(clock)

    with sim.write_vcd("ac97_waves.vcd"):
        sim.run_until(1e-6)

    