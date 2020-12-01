from nmigen import *
from nmigen.back.pysim import *

class AC97_Controller(Elaboratable):
    def __init__(self):
        #AC97 signals
        self.bit_clk_i = Signal()
        self.sdata_in = Signal()
        self.sdata_out = Signal()
        self.sync_o = Signal()
        self.reset_o = Signal()

        #ignoring modem stuff which is slots 5, 10, 11, 12
        # pcm inputs
        self.dac_left_front = Signal(20)
        self.dac_right_front = Signal(20)
        self.dac_centre = Signal(20)
        self.dac_left_surround = Signal(20)
        self.dac_right_surround = Signal(20)
        self.dac_lfe = Signal(20)
        self.dac_inputs_valid = Signal()
        self.dac_valid_ack = Signal()

        #adc outputs
        self.adc_left = Signal(20)
        self.adc_right = Signal(20)
        self.adc_mic = Signal(20)
        self.adc_outputs_valid = Signal()
        self.adc_valid_ack = Signal()

    def elaborate(self, platform):
        m = Module()




        return