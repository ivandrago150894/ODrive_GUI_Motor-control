'''
=== ENTRY 2024/02/02 ===

This code is a modifications of the running version of "PyQtGraph_Test_010.py".
This code (and all the codes from 002 to 007) works only if the configuration is done previously with the ODrive GUI.
First, power the ODrive board and wait until the cyan light turns on.
Then, connect it to the PC.
FInally, run the python code.

In this code I'm trying to:
1. Add a position control option in the GUI so you can chose between position or torque control.

==> Goal 1 Achieved!!!

The following modifications has been made to the code:

1. This version allows to perform position control instead of torque control. Hence, the code was modified only to
    do this.
2. Legend and the angular position reference signal was added to the angular position plot.

'''

import odrive # Import the ODrive API
import time
import datetime as dt
from math import *
import csv
from PyQt5 import QtWidgets, QtCore, QtGui
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QTabWidget, QGridLayout, QVBoxLayout, QHBoxLayout
#from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import sys


odrv         = odrive.find_any() # Find the ODrive board connected to any serial port
axis         = odrv.axis0
motor        = axis.motor
motor_config = axis.config.motor
ctrl_config  = axis.controller.config

motor_config.direction = 1 # To fix the rotation's direction this must be set up after the configuration is saved

axis.requested_state = 8 # Activating the close loop control mode
axis.set_abs_pos(0) # Make the current angular position the origin
ctrl_config.control_mode = 3 # https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html#ODrive.Controller.ControlMode
ctrl_config.input_mode = 3
ctrl_config.input_filter_bandwidth = 20.0
axis.controller.config.input_mode = 3 # Activate the setpoint filter
ctrl_config.pos_gain = 50.0  # Adjust the PID gains as needed
ctrl_config.vel_gain = 0.025
ctrl_config.vel_integrator_gain = 2.0
gear_ratio = 36

win_size = 200 # Quantity of data points to be displayed in the GUI when real-time plotting
t_buffer       = list([0] * win_size)
tau_buffer     = t_buffer.copy()
tau_d_buffer   = t_buffer.copy()
gearbox_buffer = t_buffer.copy()
current_buffer = t_buffer.copy()
voltage_buffer = t_buffer.copy()
pos_buffer     = t_buffer.copy()
q_d_buffer     = t_buffer.copy()

red  = pg.mkPen(color=(255, 0, 0), width = 2)
blue = pg.mkPen(color=(0, 0, 255), width = 2)

LogginButton_Flag = False
TRefBox_Flag      = False
t_0   = 0
tau_d = 0
q_d   = 0

class MainWindow(QWidget):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        global t_buffer, tau_d_buffer, tau_buffer, gearbox_buffer, current_buffer, voltage_buffer, pos_buffer, q_d_buffer,\
            t_0, t_minus_1,\
            tau_d, q_d,\
            LoggingButton, TRefBox

        self.setWindowTitle('BIRO GUI [ODrive and T-Motor]')
        
        # Layout definition (Nested layout: 3 vert. layouts nested in a hori. layout)
        MainLayout     = QHBoxLayout()
        Left_VLayout   = QVBoxLayout()
        Center_VLayout = QVBoxLayout()
        Right_VLayout  = QVBoxLayout()

        # Creating the Plot objects (Real-time data displays)
        Torque_plot  = pg.PlotWidget()
        Current_plot = pg.PlotWidget()
        Voltage_plot = pg.PlotWidget()
        Pos_plot     = pg.PlotWidget()
        Gearbox_plot = pg.PlotWidget()

        # Creating the interactive objects in the GUI
        TRefButton    = QPushButton("Send Torque command")
        LoggingButton = QPushButton("Start data Logging")

        # Adding functions to the interactive objects in the GUI        
        TRefButton.clicked.connect(TorqueReference_Clicked)
        LoggingButton.clicked.connect(LogginButton_Clicked)

        # Setup of the widgets on each layout
            # Widgets on the Left vert. layout
        Left_VLayout.addWidget(TRefButton)
        Left_VLayout.addWidget(QPushButton("Left Mid Button"))
        Left_VLayout.addWidget(LoggingButton)
            # Widgets in the center vert. layout
        TRefBox = QLineEdit(self)
        Center_VLayout.addWidget(TRefBox)
        Center_VLayout.addWidget(QPushButton("Center Mid Button"))
        Center_VLayout.addWidget(QPushButton("Center Bottom Button"))
            # Widgets in the right vert. layout
        Right_VLayout.addWidget(Torque_plot)
        Right_VLayout.addWidget(Gearbox_plot)
        Right_VLayout.addWidget(Current_plot)
        Right_VLayout.addWidget(Voltage_plot)
        Right_VLayout.addWidget(Pos_plot)

        # Adding the vert. layouts to the MainLayout (horizontal)
        MainLayout.addLayout(Left_VLayout)
        MainLayout.addLayout(Center_VLayout, stretch=1)
        MainLayout.addLayout(Right_VLayout, stretch=10)

        # Set the Main window layout
        self.setLayout(MainLayout)
        
        # Configuring the look of the plots
        label_style = {"font-size": "16px"}
        title_style = {"color": "black", "font-size": "20px"}

        Torque_plot.setTitle("Motor's torque", **title_style)
        Torque_plot.setLabel('left', "Torque [Nm]", **label_style)
        Torque_plot.setLabel('bottom', "Time [s]", **label_style)
        Torque_plot.addLegend()
        Torque_plot.setBackground('w')
        Torque_plot.showGrid(x=True, y=True)

        Gearbox_plot.setTitle("Gearbox's torque", **title_style)
        Gearbox_plot.setLabel('left', "Torque [Nm]", **label_style)
        Gearbox_plot.setLabel('bottom', "Time [s]", **label_style)
        Gearbox_plot.setBackground('w')
        Gearbox_plot.showGrid(x=True, y=True)

        Current_plot.setTitle("Motor's current", **title_style)
        Current_plot.setLabel('left', "Current [A]", **label_style)
        Current_plot.setLabel('bottom', "Time [s]", **label_style)
        Current_plot.setBackground('w')
        Current_plot.showGrid(x=True, y=True)

        Voltage_plot.setTitle("Battery's voltage", **title_style)
        Voltage_plot.setLabel('left', "Voltage [V]", **label_style)
        Voltage_plot.setLabel('bottom', "Time [s]", **label_style)
        Voltage_plot.setBackground('w')
        Voltage_plot.showGrid(x=True, y=True)

        Pos_plot.setTitle("Motor's shaft angular position", **title_style)
        Pos_plot.setLabel('left', "Angular position [deg]", **label_style)
        Pos_plot.setLabel('bottom', "Time [s]", **label_style)
        Pos_plot.addLegend()
        Pos_plot.setBackground('w')
        Pos_plot.showGrid(x=True, y=True)
        
        # Torque plot lines
        self.data_line1 = Torque_plot.plot(t_buffer, tau_buffer, name = "Actual torque", pen = red)
        self.data_line2 = Torque_plot.plot(t_buffer, tau_d_buffer, name = "Reference torque", pen = blue)
        # Gearbox plot lines
        self.data_line3 = Gearbox_plot.plot(t_buffer, gearbox_buffer, name = "Output torque", pen = red)
        # Current plot line
        self.data_line4 = Current_plot.plot(t_buffer, current_buffer, pen = red)
        # Voltage plot line
        self.data_line5 = Voltage_plot.plot(t_buffer, voltage_buffer, pen = red)
        # Angular position plot line
        self.data_line6 = Pos_plot.plot(t_buffer, pos_buffer, name = "Ang. Position", pen = red)
        self.data_line7 = Pos_plot.plot(t_buffer, q_d_buffer, name = "Reference Ang. Position", pen = blue)

        # Initialization of variables
        self.timer = QtCore.QTimer()
        self.timer.setInterval(20) # Set the refresh time-rate for the plotted data in the GUI
        t_0 = time.time() # Set the initial tim
        t_minus_1 = t_0 # Time variable to ensure that no repeated data is ploted
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()
            
       
    def update_plot_data(self):
        global t_buffer, tau_d_buffer, tau_buffer, gearbox_buffer, current_buffer, voltage_buffer, pos_buffer, q_d_buffer,\
            t_0, t_minus_1,\
            tau_d, q_d, gear_ratio,\
            LogginButton_Flag, TRefBox_Flag,\
            csv_file_name, DataHeaders,\
            TRefBox_Command
        
        t = time.time() - t_0
                
        if t_minus_1 != t:
                       
            if TRefBox_Flag != False:
                #tau_d = float(eval(TRefBox_Command))
                q_d = float(eval(TRefBox_Command))/360

            # Input the torque command
            #axis.controller.input_torque = tau_d
            axis.controller.input_pos = q_d
            tau = axis.motor.torque_estimate
            gearbox_torque = gear_ratio*tau
            V = odrv.vbus_voltage
            I = axis.motor.foc.Iq_measured
            q = axis.pos_vel_mapper.pos_abs*(360)
            dot_q = axis.pos_vel_mapper.vel * 60 * 6 # Angular velocity in deg/s (CCW+)

            t_buffer = t_buffer[1:]
            t_buffer.append(t)

            tau_buffer = tau_buffer[1:]
            tau_buffer.append(tau)

            tau_d_buffer = tau_d_buffer[1:]
            tau_d_buffer.append(tau_d)

            gearbox_buffer = gearbox_buffer[1:]
            gearbox_buffer.append(gearbox_torque)

            current_buffer = current_buffer[1:]
            current_buffer.append(I)

            voltage_buffer = voltage_buffer[1:]
            voltage_buffer.append(V)

            pos_buffer = pos_buffer[1:]
            pos_buffer.append(q)

            q_d_buffer = q_d_buffer[1:]
            q_d_buffer.append(q_d*360)
        
            self.data_line1.setData(t_buffer, tau_buffer)
            self.data_line2.setData(t_buffer, tau_d_buffer)

            self.data_line3.setData(t_buffer, gearbox_buffer)

            self.data_line4.setData(t_buffer, current_buffer)

            self.data_line5.setData(t_buffer, voltage_buffer)

            self.data_line6.setData(t_buffer, pos_buffer)
            self.data_line7.setData(t_buffer, q_d_buffer)

            if LogginButton_Flag == True:
                LoggedData = {
                    "time": t,
                    "tau_d": tau_d,
                    "tau": tau,
                    "gearbox_torque": gearbox_torque,
                    "current": I,
                    "bat_volt": V,
                    "ang_pos": q                    
                    }

                with open(csv_file_name, mode="a", newline="") as file:
                    writer = csv.DictWriter(file, fieldnames = DataHeaders)
                    writer.writerow(LoggedData)

        t_minus_1 = t


def LogginButton_Clicked():
    global LogginButton_Flag, LoggingButton, csv_file_name, DataHeaders
    LogginButton_Flag = True
    LoggingButton.setText("Logging data")
    LoggingButton.setStyleSheet("background-color : green")
    csv_file_name = "GUI_Logger_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".csv"
    DataHeaders = ["time", "tau_d", "tau", "gearbox_torque", "current", "bat_volt", "ang_pos"]

    # Create the CSV file and write the header
    with open(csv_file_name, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames = DataHeaders)
        writer.writeheader()


def TorqueReference_Clicked():
    global TRefBox, TRefBox_Flag, TRefBox_Command
    TRefBox_Flag = True
    TRefBox_Command = str(TRefBox.text())


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(app.exec_())