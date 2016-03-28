#!/usr/bin/python
# -*- coding: cp1252 -*-
#############################################################################
##
##  Author:   mba7
##  Email:    monta.bha@gmail.com
#############################################################################
""" 
A serial port packet monitor that plots live data using PyQwt.

The monitor expects to receive 8 bytes data packets with a line return
as a packet EOF on the serial port.
Each received packet is analysed to extract gx, gy and gz.

When the monitor is active, you can turn the 'Update speed' knob
to control the frequency of screen updates.

Code herited from Eli Bendersky (eliben@gmail.com)
License: this code is in the public domain
Last modified: 07.08.2009
"""

import  random, sys, Queue, serial, glob, os, csv, time

import  PyQt4.Qwt5     as Qwt
from    PyQt4.QtCore   import *
from    PyQt4.QtGui    import *

from com_monitor        import ComMonitorThread
from globals            import *



class PlottingDataMonitor(QMainWindow):
    def __init__(self, parent=None):
        super(PlottingDataMonitor, self).__init__(parent)

        self.setWindowTitle('ADXL345 Realtime Monitor')
        self.resize(800, 600)
        
        self.port           = ""
        self.baudrate       = 9600
        self.monitor_active = False                 # on/off monitor state
        self.com_monitor    = None                  # monitor reception thread
        self.com_data_q     = None
        self.com_error_q    = None
        self.livefeed       = LiveDataFeed()
        self.timer          = QTimer()
        self.g_samples      = [[], [], []]
        self.curve          = [None]*3
        self.gcurveOn       = [1]*3                 # by default all curve are plotted
        self.csvdata        = []    
        
        self.create_menu()
        self.create_main_frame()
        self.create_status_bar()

        # Activate start-stop button connections
        self.connect(self.button_Connect, SIGNAL("clicked()"),
                    self.OnStart)
        self.connect(self.button_Disconnect, SIGNAL("clicked()"),
                    self.OnStop)
    #----------------------------------------------------------


    def create_com_box(self):
        """ 
        Purpose:   create the serial com groupbox
        Return:    return a layout of the serial com
        """
        self.com_box = QGroupBox("COM Configuration")

        com_layout = QGridLayout()

        self.radio9600     =    QRadioButton("9600")
        self.radio9600.setChecked(1)
        self.radio19200    =    QRadioButton("19200")
        self.Com_ComboBox  =    QComboBox()

        com_layout.addWidget(self.Com_ComboBox,0,0,1,2)
        com_layout.addWidget(self.radio9600,1,0)
        com_layout.addWidget(self.radio19200,1,1)
        self.fill_ports_combobox()

        self.button_Connect      =   QPushButton("Start")
        self.button_Disconnect   =   QPushButton("Stop")
        self.button_Disconnect.setEnabled(False)

        com_layout.addWidget(self.button_Connect,0,2)
        com_layout.addWidget(self.button_Disconnect,1,2)        

        return com_layout
    #---------------------------------------------------------------------
   

    def create_plot(self):
        """ 
        Purpose:   create the pyqwt plot
        Return:    return a list containing the plot and the list of the curves
        """
        plot = Qwt.QwtPlot(self)
        plot.setCanvasBackground(Qt.black)
        plot.setAxisTitle(Qwt.QwtPlot.xBottom, 'Time')
        plot.setAxisScale(Qwt.QwtPlot.xBottom, 0, 10, 1)
        plot.setAxisTitle(Qwt.QwtPlot.yLeft, 'Acceleration')
        plot.setAxisScale(Qwt.QwtPlot.yLeft, YMIN, YMAX, (YMAX-YMIN)/10)
        plot.replot()
        
        curve = [None]*3
        pen = [QPen(QColor('limegreen')), QPen(QColor('red')) ,QPen(QColor('yellow')) ]
        for i in range(3):
            curve[i] =  Qwt.QwtPlotCurve('')
            curve[i].setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
            pen[i].setWidth(2)
            curve[i].setPen(pen[i])
            curve[i].attach(plot)

        return plot, curve
    #---------------------------------------------------


    def create_knob(self):
        """ 
        Purpose:   create a knob
        Return:    return a the knob widget
        """
        knob = Qwt.QwtKnob(self)
        knob.setRange(0, 180, 0, 1)
        knob.setScaleMaxMajor(10)
        knob.setKnobWidth(50)
        knob.setValue(10)
        return knob
    #---------------------------------------------------


    def create_status_bar(self):
        self.status_text = QLabel('Monitor idle')
        self.statusBar().addWidget(self.status_text, 1)
    #---------------------------------------------------


    def create_checkbox(self, label, color, connect_fn, connect_param):
        """ 
        Purpose:    create a personalized checkbox
        Input:      the label, color, activated function and the transmitted parameter
        Return:     return a checkbox widget
        """
        checkBox = QCheckBox(label)
        checkBox.setChecked(1)
        checkBox.setFont( QFont("Arial", pointSize=12, weight=QFont.Bold ) )
        green = QPalette()
        green.setColor(QPalette.Foreground, color)
        checkBox.setPalette(green)
        self.connect(checkBox, SIGNAL("clicked()"), partial(connect_fn,connect_param))
        return checkBox
        #---------------------------------------------------


    def create_main_frame(self):
        """ 
        Purpose:    create the main frame Qt widget
        """
        # Serial communication combo box
        portname_layout = self.create_com_box()
        self.com_box.setLayout(portname_layout)
        
        # Update speed knob
        self.updatespeed_knob = self.create_knob()
        self.connect(self.updatespeed_knob, SIGNAL('valueChanged(double)'),
            self.on_knob_change)
        self.knob_l = QLabel('Update speed = %s (Hz)' % self.updatespeed_knob.value())
        self.knob_l.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Create the plot and curves
        self.plot, self.curve = self.create_plot()

        # Create the configuration horizontal panel
        self.max_spin    = QSpinBox()
        self.max_spin.setMaximum(1000)
        self.max_spin.setValue(1000)
        spins_hbox      = QHBoxLayout()
        spins_hbox.addWidget(QLabel('Save every'))
        spins_hbox.addWidget(self.max_spin)
        spins_hbox.addWidget( QLabel('Lines'))
        #spins_hbox.addStretch(1)

        self.gCheckBox   =  [   self.create_checkbox("Acceleration(x)", Qt.green, self.activate_curve, 0),
                                self.create_checkbox("Acceleration(y)", Qt.red, self.activate_curve, 1),
                                self.create_checkbox("Acceleration(z)", Qt.yellow, self.activate_curve, 2)
                            ]

        self.button_clear      =   QPushButton("Clear screen")

        self.connect(self.button_clear, SIGNAL("clicked()"),
                    self.clear_screen)
        
        # Place the horizontal panel widget
        plot_layout = QGridLayout()
        plot_layout.addWidget(self.plot,0,0,8,7)
        plot_layout.addWidget(self.gCheckBox[0],0,8)
        plot_layout.addWidget(self.gCheckBox[1],1,8)
        plot_layout.addWidget(self.gCheckBox[2],2,8)
        plot_layout.addWidget(self.button_clear,3,8)
        plot_layout.addLayout(spins_hbox,4,8)
        plot_layout.addWidget(self.updatespeed_knob,5,8)
        plot_layout.addWidget(self.knob_l,6,8)
        
        plot_groupbox = QGroupBox('Acceleration')
        plot_groupbox.setLayout(plot_layout)
        
        # Place the main frame and layout
        self.main_frame = QWidget()
        main_layout 	= QVBoxLayout()
        main_layout.addWidget(self.com_box)
        main_layout.addWidget(plot_groupbox)
        main_layout.addStretch(1)
        self.main_frame.setLayout(main_layout)
        
        self.setCentralWidget(self.main_frame)
    #----------------------------------------------------------------------


    def clear_screen(self):
        g_samples[0] = []
    #-----------------------------
        

    def activate_curve(self, axe):
        if self.gCheckBox[axe].isChecked():
            self.gcurveOn[axe]  = 1
        else:
            self.gcurveOn[axe]  = 0
    #---------------------------------------


    def create_menu(self):
        self.file_menu = self.menuBar().addMenu("&File")
        
        selectport_action = self.create_action("Select COM &Port...",
            shortcut="Ctrl+P", slot=self.on_select_port, tip="Select a COM port")
        self.start_action = self.create_action("&Start monitor",
            shortcut="Ctrl+M", slot=self.OnStart, tip="Start the data monitor")
        self.stop_action = self.create_action("&Stop monitor",
            shortcut="Ctrl+T", slot=self.OnStop, tip="Stop the data monitor")
        exit_action = self.create_action("E&xit", slot=self.close, 
            shortcut="Ctrl+X", tip="Exit the application")
        
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(False)
        
        self.add_actions(self.file_menu, 
            (   selectport_action, self.start_action, self.stop_action,
                None, exit_action))
            
        self.help_menu = self.menuBar().addMenu("&Help")
        about_action = self.create_action("&About", 
            shortcut='F1', slot=self.on_about, 
            tip='About the monitor')
        
        self.add_actions(self.help_menu, (about_action,))
    #----------------------------------------------------------------------


    def set_actions_enable_state(self):
        if self.portname.text() == '':
            start_enable = stop_enable = False
        else:
            start_enable = not self.monitor_active
            stop_enable = self.monitor_active
        
        self.start_action.setEnabled(start_enable)
        self.stop_action.setEnabled(stop_enable)
    #-----------------------------------------------


    def on_about(self):
        msg = __doc__
        QMessageBox.about(self, "About the demo", msg.strip())
    #-----------------------------------------------

    

    def on_select_port(self):
        
        ports = enumerate_serial_ports()
        
        if len(ports) == 0:
            QMessageBox.critical(self, 'No ports',
                'No serial ports found')
            return
        
        item, ok = QInputDialog.getItem(self, 'Select a port',
                    'Serial port:', ports, 0, False)
        
        if ok and not item.isEmpty():
            self.portname.setText(item)            
            self.set_actions_enable_state()
    #-----------------------------------------------


    def fill_ports_combobox(self):
        """ Purpose: rescan the serial port com and update the combobox
        """
        vNbCombo = ""
        self.Com_ComboBox.clear()
        self.AvailablePorts = enumerate_serial_ports()
        for value in self.AvailablePorts:
            self.Com_ComboBox.addItem(value)
            vNbCombo += value + " - "
        vNbCombo = vNbCombo[:-3] 

        debug(("--> Les ports series disponibles sont: %s " % (vNbCombo)))
    #----------------------------------------------------------------------


    def OnStart(self):
        """ Start the monitor: com_monitor thread and the update timer     
        """
        if self.radio19200.isChecked():
            self.baudrate = 19200
            print "--> baudrate is 19200 bps"
        if self.radio9600.isChecked():
            self.baudrate = 9600
            print "--> baudrate is 9600 bps"  

        vNbCombo    = self.Com_ComboBox.currentIndex()
        self.port   = self.AvailablePorts[vNbCombo]

        self.button_Connect.setEnabled(False)
        self.button_Disconnect.setEnabled(True)
        self.Com_ComboBox.setEnabled(False)

        self.data_q      =  Queue.Queue()
        self.error_q     =  Queue.Queue()
        self.com_monitor =  ComMonitorThread(
                                            self.data_q,
                                            self.error_q,
                                            self.port,
                                            self.baudrate)
        
        self.com_monitor.start()  

        com_error = get_item_from_queue(self.error_q)
        if com_error is not None:
            QMessageBox.critical(self, 'ComMonitorThread error',
                com_error)
            self.com_monitor = None  

        self.monitor_active = True

        self.connect(self.timer, SIGNAL('timeout()'), self.on_timer)
        
        update_freq = self.updatespeed_knob.value()
        if update_freq > 0:
            self.timer.start(1000.0 / update_freq)
        
        self.status_text.setText('Monitor running')
        debug('--> Monitor running')
    #------------------------------------------------------------


    def OnStop(self):
        """ Stop the monitor
        """
        if self.com_monitor is not None:
            self.com_monitor.join(1000)
            self.com_monitor = None

        self.monitor_active = False
        self.button_Connect.setEnabled(True)
        self.button_Disconnect.setEnabled(False)
        self.Com_ComboBox.setEnabled(True)
        self.timer.stop()
        self.status_text.setText('Monitor idle')
        debug('--> Monitor idle')
    #-----------------------------------------------


    def on_timer(self):
        """ Executed periodically when the monitor update timer
            is fired.
        """
        self.read_serial_data()
        self.update_monitor()
	#-----------------------------------------------


    def on_knob_change(self):
        """ When the knob is rotated, it sets the update interval
            of the timer.
        """
        update_freq = self.updatespeed_knob.value()
        self.knob_l.setText('Update speed = %s (Hz)' % self.updatespeed_knob.value())

        if self.timer.isActive():
            update_freq = max(0.01, update_freq)
            self.timer.setInterval(1000.0 / update_freq)
    #-----------------------------------------------


    def update_monitor(self):
        """ Updates the state of the monitor window with new 
            data. The livefeed is used to find out whether new
            data was received since the last update. If not, 
            nothing is updated.
        """
        if self.livefeed.has_new_data:
            data = self.livefeed.read_data()

            self.csvdata.append([data['timestamp'], data['gx'], data['gy'], data['gz']] )
            if len(self.csvdata) > self.max_spin.value():
                f = open(time.strftime("%H%M%S")+".csv", 'wt')
                try:
                    writer = csv.writer(f)
                    for i in range(self.max_spin.value()):
                        writer.writerow( self.csvdata[i] )
                    print 'transfert data to csv after 1000 samples'
                finally:
                    f.close()
                self.csvdata = []
            
            self.g_samples[0].append(
                (data['timestamp'], data['gx']))
            if len(self.g_samples[0]) > 100:
                self.g_samples[0].pop(0)

            self.g_samples[1].append(
                (data['timestamp'], data['gy']))
            if len(self.g_samples[1]) > 100:
                self.g_samples[1].pop(0)

            self.g_samples[2].append(
                (data['timestamp'], data['gz']))
            if len(self.g_samples[2]) > 100:
                self.g_samples[2].pop(0)

            tdata = [s[0] for s in self.g_samples[2]]

            for i in range(3):
                data[i] = [s[1] for s in self.g_samples[i]]
                if self.gcurveOn[i]:
                    self.curve[i].setData(tdata, data[i])

            """
            debug("xdata", data[0])
            debug("ydata", data[1])
            debug("tdata", data[2])
            """

            self.plot.setAxisScale(Qwt.QwtPlot.xBottom, tdata[0], max(5, tdata[-1]) )        
            
            self.plot.replot()
    #-----------------------------------------------
            
            
    def read_serial_data(self):
        """ Called periodically by the update timer to read data
            from the serial port.
        """
        qdata = list(get_all_from_queue(self.data_q))
        # get just the most recent data, others are lost
        #print "qdata" , qdata
        if len(qdata) > 0:
            data = dict(timestamp=qdata[-1][1], 
                        gx=qdata[-1][0][0],
                        gy=qdata[-1][0][1],
                        gz=qdata[-1][0][2]
                        )
            self.livefeed.add_data(data)
    #-----------------------------------------------


    
    # The following two methods are utilities for simpler creation
    # and assignment of actions
    #
    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)
    #-----------------------------------------------


    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action
    #-----------------------------------------------

    

def main():
    app = QApplication(sys.argv)
    form = PlottingDataMonitor()
    form.show()
    app.exec_()


if __name__ == "__main__":
    main()
    
    

