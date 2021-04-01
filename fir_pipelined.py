from nmigen import *
from nmigen.sim import *
import math
from scipy import signal

class FIR_Pipelined(Elaboratable):
    def __init__(self, width = 16, taps=16, cutoff=0.5, filter_type='lowpass', 
        output_width = None, macc_width=32):
 
        fir_coeff = (signal.firwin(taps, cutoff, pass_zero=filter_type)*2**(width-1))
        self.coefficients = []
        for n in range(0, taps):
            self.coefficients.append(round(fir_coeff[n]))
        self.coefficients.append(0)

        if(width*2 > macc_width):
            raise ValueError('MACC width must be at least 2*sample width')
        #if((width*2 + math.ceil(math.log2(taps))) >= macc_width):
        #    print("Warning! Possible insufficient guard bits, potential MACC overflow!")
        if output_width == None:
            self.output_width = width
        else:
            self.output_width = output_width
        self.macc_width = macc_width
        self.width = width
        self.sample = Shape(width=self.width, signed=True)
        self.taps = len(self.coefficients)-1
        self.latency = self.taps + 3    # min. number of clock cycles per sample

        self.input = Signal(shape = self.sample) 
        self.input_ready_i = Signal()
        self.output = Signal(signed(self.output_width)) 
        self.output_ready_o = Signal()  
        self.accumulator = Signal(shape = Shape(width=self.macc_width, signed=True))      

    def elaborate(self, platform):
        m = Module()

        sample_count = Signal(math.ceil(math.log2(self.taps)))
        reset_acc = Signal()
        multiplicand1 = Signal(shape = self.sample) 
        multiplicand2 = Signal(shape = self.sample) 

        samples = Memory(width=self.width, depth=self.taps, 
            name = "samples")

        m.d.comb += [
            multiplicand1.eq(samples[sample_count]),
            reset_acc.eq(0)
        ]
        m.d.sync += self.output_ready_o.eq(0)

        with m.Switch(sample_count):
            for n in range(0, self.taps+1):
                with m.Case(n):
                    m.d.comb += multiplicand2.eq(self.coefficients[n])

        accumulator = self.accumulator 
        fabric_multiply = False 
        if ((platform == None) or fabric_multiply):
            m.d.sync += accumulator.eq(accumulator + (multiplicand1*multiplicand2))
            with m.If(reset_acc):
                m.d.sync += accumulator.eq(0)
        else:
            with open('inferred_mult.v') as f:
                platform.add_file('inferred_mult.v', f)
            m.submodules.dsp = Instance(
                'dsp48e_macc_latency1_16bit',
                i_clk = ClockSignal(),
                i_rst_sync = reset_acc,
                i_a = multiplicand1,
                i_b = multiplicand2,
                o_accumulator = accumulator
            )

        with m.FSM() as fir_fsm:
            with m.State("WAIT"):
                m.next = "WAIT"
                m.d.comb += reset_acc.eq(1) 
                with m.If(self.input_ready_i):
                    m.next = "LOAD"           

            with m.State("LOAD"):
                m.next = "PROCESSING"
                m.d.sync += samples[0].eq(self.input)  
                for i in range(1, self.taps):
                        m.d.sync += samples[i].eq(samples[i-1])
                m.d.comb += reset_acc.eq(1)                                 

            with m.State("PROCESSING"):
                m.next = "PROCESSING"
                m.d.sync += sample_count.eq(sample_count+1) 
                with m.If(sample_count==(self.taps-1)):
                    m.next = "PIPELINE_CLEAR"
            
            with m.State("PIPELINE_CLEAR"):
                # wait as many clock cycles as needed for the pipeline in DSP to finish then
                m.d.sync += sample_count.eq(0)
                m.next = "SAVE"

            with m.State("SAVE"):
                m.next = "WAIT"
                m.d.sync += [
                    self.output_ready_o.eq(1),
                    self.output.eq(accumulator[(2*self.width)-self.output_width:2*self.width]),
                ]                

        return m

if __name__=="__main__":

    freq_response = False
    
    def clock():
        while True:
            yield

    def wait_output_ready():
        while (not (yield dut.output_ready_o)):
            yield

    def input_signal(t):
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
            yield dut.input.eq(round(input_signal(t)*(2**15 -1)))
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

    
    if(not freq_response):

        dut = FIR_Pipelined(width=16, macc_width=48,
        taps=33, cutoff=0.5, filter_type='lowpass')
        sim = Simulator(dut)
        sim.add_clock(10e-9) #100MHz
        sim.add_sync_process(clock)
        sim.add_sync_process(tb)

        with sim.write_vcd("fir_waves.vcd"):
            sim.run_until(5e-5, run_passive=True)
    
    else:
        
        fir_taps = 33
        # frequency is (w/pi)*1000 kHz
        # max w is pi. (represents nyquist rate)
        omega = 0.2
        def freq_tb():
            yield dut.input.eq(0)
            yield dut.output.eq(0)
            yield
            for t in range(0,1000):      #100 samples with a 50 clock cycle sampling period 
                yield dut.input_ready_i.eq(1)    # (500ns, 2MHz sample rate)            
                yield dut.input.eq(round(math.sin(omega*t)*(2**17 -1)))
                yield
                yield dut.input_ready_i.eq(0)
                for n in range(0, 49):
                    yield

        max_output = 0
        def find_max_out():
            global max_output
            max_output = 0
            for n in range(0, 50*fir_taps): # let the transient settle
                    yield
            while True:
                out = yield dut.output
                if(abs(out) > max_output):
                    max_output = abs(out)
                for n in range(0, 40):
                    yield
        
        # fs/2 = 1000kHz
        dut = FIR_Pipelined(width=18, macc_width=48,
        taps=33, cutoff=0.001, filter_type='highpass')

        def find_gain(frequency):
            global omega
            omega = (frequency*3.14)/1000
            sweep = Simulator(dut)
            sweep.add_clock(10e-9) #100MHz
            sweep.add_sync_process(clock)
            sweep.add_sync_process(find_max_out) 
            sweep.add_sync_process(freq_tb)       
            sweep.run_until(5e-5, run_passive=True)
            return max_output/(2**17-1)

        with open("frequency_sweep.csv", "w") as gains_out:
            gains_out.write('Freq (kHz), Gain, Gain(dB) \n')
            for decade in range(0, 3):
                for step in range(1, 20):
                    f = 0.5*step*(10**decade)
                    gain = str(find_gain(f))
                    gains_out.write(str(f) + ',' + gain + '\n')

