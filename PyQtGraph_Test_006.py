'''
=== ENTRY 2024/01/12 ===

This code is a modifications of the running version of "PyQtGraph_Test_005.py".
In this code I'm trying to achive send a torque reference command through the GUI.

==> The QLineEdit widget was added to input a custom torque command.
    Currently working for constant torque commands!!!

'''

import odrive # Import the ODrive API
#from odrive.enums import *
import time
import datetime as dt
#import matplotlib.pyplot as plt
#import matplotlib.animation as animation
import math
import csv
from PyQt5 import QtWidgets, QtCore, QtGui
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QTabWidget, QGridLayout, QVBoxLayout, QHBoxLayout
#from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import sys

# Shortening some commands
odrv         = odrive.find_any() # Find the ODrive board connected to any serial port
axis         = odrv.axis0
motor        = axis.motor
motor_config = axis.config.motor
ctrl_config  = axis.controller.config

KV_rating = 380
motor_config.pole_pairs = 12 # Number of magnet poles in the rotor, divided by two.
motor_config.torque_constant = 8.27/KV_rating
motor_config.direction = 1
motor_config.phase_resistance = 0.113
motor_config.phase_inductance = 0.00005702
motor_config.phase_resistance_valid = True
motor_config.phase_inductance_valid = True

# Activating the close loop control mode
axis.set_abs_pos(0)
axis.requested_state = 8

'''# Gathering the sensed data
    V   = odrv.vbus_voltage # Read the Voltage on the DC bus as measured by the ODrive.
    I   = axis.motor.foc.Iq_measured # Current in A that is responsible of the torque
    tau = axis.motor.torque_estimate # Torque estimate in Nm (based on the toque constant)

    if tdata_prev != t_data:
        with open(csv_file_name, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames = DataHeaders)
            writer.writerow(LoggedData)


# Setup the initial time
t_0 = time.time()
tdata_prev = 0

csv_file_name = time.strftime("%Y-%m-%d_%H-%M-%S") + ".csv"
DataHeaders = ["time", "tau_d", "tau", "current", "bat_volt"]

# Create the CSV file and write the header
with open(csv_file_name, mode="w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames = DataHeaders)
    writer.writeheader()
'''

LogginButton_activated = False

win_size = 200 # Quantity of data points to be displayed in the GUI when real-time plotting
t_buffer       = list([0] * win_size)
tau_buffer     = t_buffer.copy()
tau_d_buffer   = t_buffer.copy()
current_buffer = t_buffer.copy()
voltage_buffer = t_buffer.copy()
pos_buffer     = t_buffer.copy()

red  = pg.mkPen(color=(255, 0, 0), width = 2)
blue = pg.mkPen(color=(0, 0, 255), width = 2)

class MainWindow(QWidget):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        global win_size, t_buffer, tau_d_buffer, tau_buffer, current_buffer, voltage_buffer, pos_buffer, t_0, t_minus_1, LoggingButton, TRefBox, tau_d

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
        # Definition of the widgets on each layout
            # Widgets on the Left vert. layout
        TRefButton = QPushButton("Send Torque command")
        Left_VLayout.addWidget(TRefButton)
        Left_VLayout.addWidget(QPushButton("Left Mid Button"))
        LoggingButton = QPushButton("Start data Logging")
        Left_VLayout.addWidget(LoggingButton)
        # Adding functions to the buttons
        LoggingButton.clicked.connect(LogginButton_Clicked)
        TRefButton.clicked.connect(TorqueReference_Clicked)
            # Widgets in the center vert. layout
        TRefBox = QLineEdit(self)
        Center_VLayout.addWidget(TRefBox)
        Center_VLayout.addWidget(QPushButton("Center Mid Button"))
        Center_VLayout.addWidget(QPushButton("Center Bottom Button"))
            # Widgets in the right vert. layout
        Right_VLayout.addWidget(QLabel("Right Motor"))
        Right_VLayout.addWidget(Torque_plot)
        Right_VLayout.addWidget(Current_plot)
        Right_VLayout.addWidget(Voltage_plot)
        Right_VLayout.addWidget(Pos_plot)

        # Adding the vert. layouts to the MainLayout (horizontal)
        MainLayout.addLayout(Left_VLayout)
        MainLayout.addLayout(Center_VLayout)
        MainLayout.addLayout(Right_VLayout)

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
        Pos_plot.setBackground('w')
        Pos_plot.showGrid(x=True, y=True)
        
        # Torque plot lines
        self.data_line1 = Torque_plot.plot(t_buffer, tau_buffer, name = "Actual torque", pen = red)
        self.data_line2 = Torque_plot.plot(t_buffer, tau_d_buffer, name = "Reference torque", pen = blue)
        # Current plot line
        self.data_line3 = Current_plot.plot(t_buffer, current_buffer, pen = red)
        # Voltage plot line
        self.data_line4 = Voltage_plot.plot(t_buffer, voltage_buffer, pen = red)
        # Angular position plot line
        self.data_line5 = Pos_plot.plot(t_buffer, pos_buffer, pen = red)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(20)
        t_0 = time.time()
        tau_d = 0
        t_minus_1 = t_0
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()
            
       
    def update_plot_data(self):

        global win_size, t_buffer, tau_d_buffer, tau_buffer, current_buffer, voltage_buffer,\
                pos_buffer, t_0, t_minus_1, LogginButton_activated, csv_file_name, DataHeaders,\
                tau_d

        t = time.time() - t_0
                
        if t_minus_1 != t:
            # Define the sinwave parameters and Computing the desired torque command
            '''amp   = 0.05
            cyti  = 5 # Cycle time (time in seconds to achieve one cycle)
            freq  = (2*math.pi)/cyti
            tau_d = amp*math.sin(t*freq)'''

            # Input the torque command
            axis.controller.input_torque = tau_d
            tau = axis.motor.torque_estimate
            V = odrv.vbus_voltage
            I = axis.motor.foc.Iq_measured
            q = axis.pos_vel_mapper.pos_abs*(360)

            t_buffer = t_buffer[1:]
            t_buffer.append(t)

            tau_buffer = tau_buffer[1:]
            tau_buffer.append(tau)

            tau_d_buffer = tau_d_buffer[1:]
            tau_d_buffer.append(tau_d)

            current_buffer = current_buffer[1:]
            current_buffer.append(I)

            voltage_buffer = voltage_buffer[1:]
            voltage_buffer.append(V)

            pos_buffer = pos_buffer[1:]
            pos_buffer.append(q)
        
            self.data_line1.setData(t_buffer, tau_buffer)
            self.data_line2.setData(t_buffer, tau_d_buffer)

            self.data_line3.setData(t_buffer, current_buffer)

            self.data_line4.setData(t_buffer, voltage_buffer)

            self.data_line5.setData(t_buffer, pos_buffer)

            if LogginButton_activated == True:
                LoggedData = {
                    "time": t,
                    "tau_d": tau_d,
                    "tau": tau,
                    "current": I,
                    "bat_volt": V,
                    "ang_pos": q                    
                    }

                with open(csv_file_name, mode="a", newline="") as file:
                    writer = csv.DictWriter(file, fieldnames = DataHeaders)
                    writer.writerow(LoggedData)

        t_minus_1 = t

def LogginButton_Clicked():
    global LogginButton_activated, csv_file_name, DataHeaders, LoggingButton
    LogginButton_activated = True
    LoggingButton.setText("Logging data")
    LoggingButton.setStyleSheet("background-color : green")
    csv_file_name = "GUI_Logger_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".csv"
    DataHeaders = ["time", "tau_d", "tau", "current", "bat_volt", "ang_pos"]

    # Create the CSV file and write the header
    with open(csv_file_name, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames = DataHeaders)
        writer.writeheader()
    #print("Logging button pressed")
        
def TorqueReference_Clicked():
    global TRefBox, tau_d
    tau_d = eval(TRefBox.text())

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(app.exec_())