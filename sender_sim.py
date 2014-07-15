#!/usr/bin/env python

import random, time, math, os, serial

if os.name  == 'nt':
    port = "com1"
else:
    port = "/dev/tty.com1"

ser = serial.Serial(port, 9600)


incycle = 0

while True:
    a = int(random.randint(60, 80) * (1 + math.sin(incycle)))
    b = int(random.randint(60, 80) * (1 + math.sin(incycle)))
    c = int(random.randint(60, 80) * (1 + math.sin(incycle)))

    # send a sequence of 6 bytes followed by space (end of frame marker)
    data = chr(a) + " " + chr(0) + " " + chr(b) + " " + chr(1) + " " + chr(c)+ " " + chr(0)
    x = ser.write(data+'\n')
      
    time.sleep(0.02)
    
    incycle += 0.01
    if incycle >= 2 * math.pi:
        incycle = 0

ser.close()

