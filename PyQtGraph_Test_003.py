'''
This code is for testing if the configuration that is saved in the ODrive GUI is saved
into the dcevice and can work without configuring the values in this script.

THE PREVIOUS WORKS!!! [2023/12/05]

With this code a window opens and displays real-time data (reference torque and current torque)

THIS WORKS!!! [2023/12/05]

=== ENTRY 2023/12/06 ===

Now different data is displayed in real-time in the same window.
Displays: Reference torque, current torque, current, voltage, and angular position

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
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QTabWidget, QGridLayout, QVBoxLayout
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
            writer = csv.DictWriter(file, fieldnames = data_names)
            writer.writerow(sensor_data)


# Setup the initial time
t_0 = time.time()
tdata_prev = 0

csv_file_name = time.strftime("%Y-%m-%d_%H-%M-%S") + ".csv"
data_names = ["time", "tau_d", "tau", "current", "bat_volt"]

# Create the CSV file and write the header
with open(csv_file_name, mode="w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames = data_names)
    writer.writeheader()
'''

t_buffer       = []
tau_buffer     = []
tau_d_buffer   = []
current_buffer = []
voltage_buffer = []
q_buffer       = []

start_time = time.time()
red  = pg.mkPen(color=(255, 0, 0))
blue = pg.mkPen(color=(0, 0, 255), width = 2)

class MainWindow(QWidget):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        global t_buffer, tau_d_buffer, tau_buffer, current_buffer, voltage_buffer, q_buffer

        self.setWindowTitle('BIRO GUI [ODrive and T-Motor]')
        self.setGeometry(0, 0, 1200, 1200)

        MainLayout = QGridLayout()
        VertLayout_1 = QVBoxLayout()

        self.Element_1 = QWidget()
        self.Element_1.layout = QVBoxLayout()
    

        self.Plot_1   = pg.PlotWidget()
        self.Plot_2   = pg.PlotWidget()
        self.Plot_3   = pg.PlotWidget()
        self.Plot_4   = pg.PlotWidget()
        self.lineEdit = QLineEdit()
        self.Button_1 = QPushButton('Print')

        self.Element_1.layout.addWidget(QLabel('<font size=8><b> Left motor torque tracking </font'))
        self.Element_1.layout.addWidget(self.Plot_1)
        self.Element_1.layout.addWidget(self.Plot_2)
        self.Element_1.layout.addWidget(self.Plot_3)
        self.Element_1.layout.addWidget(self.Plot_4)
        
        self.Element_1.setLayout(self.Element_1.layout)

        self.tab_1 = QTabWidget()
        self.tab_1.addTab(self.Element_1, 'Tab 1')

        MainLayout.addWidget(self.tab_1, 0, 0)
        self.setLayout(MainLayout)

        self.Plot_1.setBackground('w')
        self.Plot_1.showGrid(x=True, y=True)

        self.Plot_2.setBackground('w')
        self.Plot_2.showGrid(x=True, y=True)

        self.Plot_3.setBackground('w')
        self.Plot_3.showGrid(x=True, y=True)

        self.Plot_4.setBackground('w')
        self.Plot_4.showGrid(x=True, y=True)

        win_size = 500 # Quantity of data points to be displayed in the GUI when real-time plotting

        self.x = list([0] * win_size)
        self.y = list([0] * win_size)

        t_buffer       = self.x.copy()

        tau_buffer     = self.y.copy()
        tau_d_buffer   = self.y.copy()
        current_buffer = self.y.copy()
        voltage_buffer = self.y.copy()
        q_buffer       = self.y.copy()

        self.data_line1 = self.Plot_1.plot(t_buffer, tau_buffer, pen = red)
        self.data_line2 = self.Plot_1.plot(t_buffer, tau_d_buffer, pen = blue)

        self.data_line3 = self.Plot_2.plot(t_buffer, current_buffer, pen = red)

        self.data_line4 = self.Plot_3.plot(t_buffer, voltage_buffer, pen = red)

        self.data_line5 = self.Plot_4.plot(t_buffer, q_buffer, pen = red)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()
            
       
    def update_plot_data(self):

        global t_buffer, tau_d_buffer, tau_buffer, current_buffer, voltage_buffer, q_buffer

        current_time = time.time() - start_time

        # Define the sinwave parameters and Computing the desired torque command
        amp   = 0.05
        cyti  = 5 # Cycle time (time in seconds to achieve one cycle)
        freq  = (2*math.pi)/cyti
        tau_d = amp*math.sin(current_time*freq)

        # Input the torque command
        axis.controller.input_torque = tau_d
        V = odrv.vbus_voltage
        I = axis.motor.foc.Iq_measured
        q = axis.pos_vel_mapper.pos_abs*(360)

        self.x = self.x[1:]
        self.x.append(current_time)
        t_buffer = self.x

        #tau_buffer = tau_buffer.append(axis.motor.torque_estimate)
        self.y = list(tau_buffer)
        self.y = self.y[1:]
        self.y.append(axis.motor.torque_estimate)
        tau_buffer = self.y.copy()

        self.y = list(tau_d_buffer)
        self.y = self.y[1:]
        self.y.append(tau_d)
        tau_d_buffer = self.y.copy()

        self.y = list(current_buffer)
        self.y = self.y[1:]
        self.y.append(I)
        current_buffer = self.y.copy()

        self.y = list(voltage_buffer)
        self.y = self.y[1:]
        self.y.append(V)
        voltage_buffer = self.y.copy()

        self.y = list(q_buffer)
        self.y = self.y[1:]
        self.y.append(q)
        q_buffer = self.y.copy()
        
        self.data_line1.setData(t_buffer, tau_buffer)
        self.data_line2.setData(t_buffer, tau_d_buffer)

        self.data_line3.setData(t_buffer, current_buffer)

        self.data_line4.setData(t_buffer, voltage_buffer)

        self.data_line5.setData(t_buffer, q_buffer)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(app.exec_())