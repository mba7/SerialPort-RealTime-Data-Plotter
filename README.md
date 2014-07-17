SerialPort-Data-Monitor
========================

Prerequisites: Python - pyqwt - numpy - pyserial - csv

A serial port real time data monitor that plots live data using PyQwt.
In this case the plotted data are the acceleration (gx, gy, gz) measured by the ADXL345 accelerometer and send via an arduino through the serial port.

![ADXL345-Monitor](https://www.dropbox.com/s/cuch13f61r8kpm4/ADXL345-Monitor.png "ADXL345-Monitor")

The monitor expects to receive 6 bytes data packets with a line return
as a packet EOF on the serial port and a space as byte seperator.
Each received packet is analysed to extract gx, gy and gz.

The serial packet respect the following rules:
- 3 inputs, every input is a 2 bytes (Two's complement for ADXL345)
- 6 bytes seperated by a space
- the packet is a string terminated by  '\n'

This format could be easily adapted.
See sender_sim.py for example of the transmitted data to be plotted

When the monitor is active, you can:
- turn the 'Update speed' knob to control the frequency of screen updates.
- activate or deactivate each channel
- change the length of csv file to save (containing the data + a timestamp)


The code could be emulated with a simulated data sender script: 

- create a twisted virtual serial port (com1 and com2): using socat on mac : https://github.com/clokey/PublicCode/tree/master/MacOSXVirtualSerialPort and virtuel serial port driver on windows
- launch sender_sim.py (com1)
- launch plotting_data_monitor.pyw (com2)


Code inspired from Eli Bendersky work
http://eli.thegreenplace.net/2009/08/07/a-live-data-monitor-with-python-pyqt-and-pyserial/


mba7
monta.bha@gmail.com