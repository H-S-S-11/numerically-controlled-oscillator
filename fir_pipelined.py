from nmigen import *
from nmigen.sim import *
import math
from scipy import signal

class FIR_Pipelined(Elaboratable):
    def __init__(self, width = 16, taps=16, cutoff=0.5, filter_type='lowpass', macc_width=32):
 
        fir_coeff = (signal.firwin(taps, cutoff, pass_zero=filter_type)*2**(width-1))
        self.coefficients = []
        for n in range(0, taps):
            self.coefficients.append(round(fir_coeff[n]))

        if(width*2 > macc_width):
            raise ValueError('MACC width must be at least 2*sample width')
        if((width*2 + math.ceil(math.log2(taps))) >= macc_width):
            print("Warning! Possible insufficient guard bits, potential MACC overflow!")
        self.macc_width = macc_width
        self.width = width
        self.sample = Shape(width=self.width, signed=True)
        self.taps = len(self.coefficients)
        self.latency = self.taps + 3    # min. number of clock cycles per sample

        self.input = Signal(shape = self.sample) 
        self.input_ready_i = Signal()
        self.output = Signal(shape = self.sample) 
        self.output_ready_o = Signal()        

    def elaborate(self, platform):
        m = Module()

        sample_count = Signal(math.ceil(math.log2(self.taps)))
        accumulator = Signal(shape = Shape(width=self.macc_width, signed=True))
        multiply_result = Signal(shape = Shape(width=self.macc_width, signed=True))

        multiplicand1 = Signal(shape = self.sample) 
        multiplicand2 = Signal(shape = self.sample) 

        coefficients = Memory(width=self.width, depth=self.taps, 
            init=self.coefficients, name="coefficients")
        samples = Memory(width=self.width, depth=self.taps, 
            name = "samples")

        m.d.comb += [
            multiply_result.eq(multiplicand1*multiplicand2),
            multiplicand1.eq(samples[sample_count]),
            multiplicand2.eq(coefficients[sample_count]),
        ]

        m.d.sync += [
            self.output_ready_o.eq(0),
            accumulator.eq(accumulator + multiply_result),
        ]

        with m.FSM() as fir_fsm:
            with m.State("WAIT"):
                m.next = "WAIT"
                m.d.sync += accumulator.eq(0)   
                with m.If(self.input_ready_i):
                    m.next = "LOAD"           

            with m.State("LOAD"):
                m.next = "PROCESSING"
                for i in range(1, self.taps):
                        m.d.sync += samples[i].eq(samples[i-1])
                m.d.sync += [
                    accumulator.eq(0),
                    samples[0].eq(self.input),                    
                ]

            with m.State("PROCESSING"):
                m.next = "PROCESSING"
                m.d.sync += sample_count.eq(sample_count+1) 
                with m.If(sample_count==(self.taps-1)):
                    m.d.sync += sample_count.eq(0)
                    m.next = "SAVE"

            with m.State("SAVE"):
                m.next = "WAIT"
                m.d.sync += [
                    self.output_ready_o.eq(1),
                    self.output.eq(accumulator[self.width:self.width*2]),
                ]                

        return m


if __name__=="__main__":
    #from scipy import signal
    import math

    dut = FIR_Pipelined(taps=32, width=18, macc_width=48)
    sim = Simulator(dut)
    sim.add_clock(10e-9) #100MHz

    def clock():
        while True:
            yield

    def wait_output_ready():
        while (not (yield dut.output_ready_o)):
            yield

    def signal(t):
        # frequency is (w/pi) MHz
        # max w is pi. (represents nyquist rate). default filter cutoff is 1.57
        w1 = 0.5
        w2 = 1
        return ( math.sin(w1*t) + 0*math.sin(w2*t) )

    def tb():
        yield dut.input.eq(2**15 -1)    # calibrate waves for gtkwave
        yield dut.output.eq(2**15 -1)   
        yield
        yield dut.input.eq(-2**15)
        yield dut.output.eq(-2**15)
        yield
        yield dut.input.eq(0)
        yield dut.output.eq(0)
        yield
        for t in range(0,1000):      #100 samples with a 50 clock cycle sampling period 
            yield dut.input_ready_i.eq(1)    # (500ns, 2MHz sample rate. default filter has 500kHz cutoff)            
            yield dut.input.eq(round(signal(t)*(2**15 -1)))
            yield
            yield dut.input_ready_i.eq(0)
            for n in range(0, 49):
                yield
        # gain of just over 0.5 at 50kHz, -3dB
        # 0.5 at 100kHz, -3dB
        # 0.485 at 200kHz 
        # 0.500 at 300kHz
        # 0.38 at 400kHz
        # 0.3 at 500kHz, -5dB
        # 0.037 at 640kHz, -14dB
        # 0.0018 at 800 kHz, -27dB
        # 0.0006 at 950kHz, -32dB
        # 0.00003 at 1MHz, -45dB (square wave, max amplitude in results in alternating 0/-1. nyquist rate reached)

    sim.add_sync_process(clock)
    sim.add_sync_process(tb)

    with sim.write_vcd("fir_waves.vcd"):
        sim.run_until(5e-5, run_passive=True)
