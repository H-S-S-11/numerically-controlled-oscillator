from scipy.signal.signaltools import sosfilt
import serial
import numpy as np
import matplotlib.pyplot as plt
import sys
from scipy import signal

fpga_value = []
esp_value  = []

esp = serial.Serial('COM5', 9600)
ser = serial.Serial('COM8', 9600)

try:
    while True:
        try:
            line = esp.readline()
            esp_value. append( int(str(line)[2:-5]) )
            fpga_value.append( int(str(ser.read())[2], 16) )

        except ValueError:
            pass
except KeyboardInterrupt:
    if len(fpga_value) < len(esp_value):
        fpga_value.append( int(str(ser.read())[2], 16)    )
    pass

esp.close()
ser.close()
            
x = np.arange(len(fpga_value))
fpga_value = np.array(fpga_value)
esp_value  = np.array(esp_value )

esp_value = esp_value * 15/1024

sos = signal.ellip(21, 0.009, 80, 0.01, output='sos')
filtered = sosfilt(sos, fpga_value)

plt.plot(x, fpga_value)
plt.plot(x, esp_value)
plt.figure()

plt.plot(x, filtered)
plt.plot(x, esp_value)
plt.ylim(0, 16)
plt.show()
