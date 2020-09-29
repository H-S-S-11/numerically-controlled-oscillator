from nmigen import *
from nmigen.back.pysim import *

class NCO_LUT(Elaboratable):
    def __init__(self):
        phi_inc = Signal(32)

    def elaborate(self, platform):