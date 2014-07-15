SerialPort-Data-Monitor
========================

Prerequisites: Python - pyqwt - numpy - pyserial - csv

A serial port real time data monitor that plots live data using PyQwt.
In this case the plotted data are the acceleration (gx, gy, gz) measured by the ADXL345 accelerometer and send via an arduino through the serial port.
Any serial packet that respect this format could be plotted correctly:

- 3 inputs, every input is a 2 bytes
- 6 bytes seperated by a space
- the packet is a string terminated by  '\n'

See sende_sim.py for example of plotted data

![ADXL345-Monitor](https://www.dropbox.com/s/cuch13f61r8kpm4/ADXL345-Monitor.png "ADXL345-Monitor")

The monitor expects to receive 8 bytes data packets with a line return
as a packet EOF on the serial port.
Each received packet is analysed to extract gx, gy and gz.
test

When the monitor is active, you can turn the 'Update speed' knob
to control the frequency of screen updates.

Code inspired from Eli Bendersky work
http://eli.thegreenplace.net/2009/08/07/a-live-data-monitor-with-python-pyqt-and-pyserial/

The code could be emulated using 
- launch sender_sim.py (com1)
- launch plotting_data_monitor.pyw (com2)

com1 and com2 are a virtual serial port
created using socat on mac : https://github.com/clokey/PublicCode/tree/master/MacOSXVirtualSerialPort
and virtuel serial port driver on windows