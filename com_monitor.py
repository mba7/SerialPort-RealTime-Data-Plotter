
import Queue, threading, time, serial
from globals            import *



class ComMonitorThread(threading.Thread):
    """ A thread for monitoring a COM port. The COM port is 
        opened when the thread is started.
    
        data_q:
            Queue for received data. Items in the queue are
            (data, timestamp) pairs, where data is a binary 
            string representing the received data, and timestamp
            is the time elapsed from the thread's start (in 
            seconds).
        
        error_q:
            Queue for error messages. In particular, if the 
            serial port fails to open for some reason, an error
            is placed into this queue.
        
        port:
            The COM port to open. Must be recognized by the 
            system.
        
        port_baud/stopbits/parity: 
            Serial communication parameters
        
        port_timeout:
            The timeout used for reading the COM port. If this
            value is low, the thread will return data in finer
            grained chunks, with more accurate timestamps, but
            it will also consume more CPU.
    """
    def __init__(   self, 
                    data_q, error_q, 
                    port_num,
                    port_baud,
                    port_stopbits = serial.STOPBITS_ONE,
                    port_parity   = serial.PARITY_NONE,
                    port_timeout  = 0.01):
        threading.Thread.__init__(self)
        
        self.serial_port = None
        self.serial_arg  = dict( port      = port_num,
                                 baudrate  = port_baud,
                                 stopbits  = port_stopbits,
                                 parity    = port_parity,
                                 timeout   = port_timeout)

        self.data_q   = data_q
        self.error_q  = error_q
        
        self.alive    = threading.Event()
        self.alive.set()
    #------------------------------------------------------


    def getAxes(self, bytes, gforce = True):
        
        x = bytes[0] | (bytes[1] << 8)
        
        if(x & (1 << 16 - 1)):
            x = x - (1<<16)

        y = bytes[2] | (bytes[3] << 8)
        if(y & (1 << 16 - 1)):
            y = y - (1<<16)

        z = bytes[4] | (bytes[5] << 8)
        if(z & (1 << 16 - 1)):
            z = z - (1<<16)

        x = x * SCALE_MULTIPLIER 
        y = y * SCALE_MULTIPLIER
        z = z * SCALE_MULTIPLIER

        if gforce == False:
            x = x * EARTH_GRAVITY_MS2
            y = y * EARTH_GRAVITY_MS2
            z = z * EARTH_GRAVITY_MS2

        x = round(x, 3)
        y = round(y, 3)
        z = round(z, 3)

        return {"x": x, "y": y, "z": z}
    #------------------------------------------------------

        
    def run(self):
        try:
            if self.serial_port: 
                self.serial_port.close()
            self.serial_port = serial.Serial(**self.serial_arg)
        except serial.SerialException, e:
            self.error_q.put(e.message)
            return
        
        # Restart the clock
        startTime = time.time()
        
        while self.alive.isSet():
          
            Line = self.serial_port.readline()
            bytes = Line.split()
            print bytes
            #use map(int) for simulation
            data = map(ord, bytes)
            qdata = [0,0,0]
            if len(data) == 6:
                timestamp = time.time() - startTime
                #data = list(map(ord, list(Line)))

                print "Line", Line
                print "bytes", bytes
                print "data", data
                
                axes = self.getAxes(data)

                print "   x = %.3fG" % ( axes['x'] )
                print "   y = %.3fG" % ( axes['y'] )
                print "   z = %.3fG" % ( axes['z'] )
                
                qdata[0] = axes['x']
                qdata[1] = axes['y']
                qdata[2] = axes['z']
                print "qdata :", qdata
                timestamp = time.clock()
                self.data_q.put((qdata, timestamp))

               
            
        # clean up
        if self.serial_port:
            self.serial_port.close()

    def join(self, timeout=None):
        self.alive.clear()
        threading.Thread.join(self, timeout)

