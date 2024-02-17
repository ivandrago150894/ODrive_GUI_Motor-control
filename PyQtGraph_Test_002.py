'''
This code is for testing if the configuration that is saved in the ODrive GUI is saved
into the dcevice and can work without configuring the values in this script.

THE PREVIOUS WORKS!!! [2023/12/05]

With this code a window opens and displays real-time data (reference torque and current torque)

THIS WORKS!!! [2023/12/05]
'''
import odrive # Import the ODrive API
#from odrive.enums import *
import time
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import math
import csv
from PyQt5 import QtWidgets, QtCore
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
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

t_buffer = []
tau_buffer = []
tau_d_buffer = []

start_time = time.time()
red  = pg.mkPen(color=(255, 0, 0))
blue = pg.mkPen(color=(0, 0, 255), width = 2)

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        global tau_buffer
        global tau_d_buffer
        global t_buffer

        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)
        self.graphWidget.setBackground('w')
        self.graphWidget.showGrid(x=True, y=True)

        self.x = list([0] * 1000)
        t_buffer = self.x.copy()
        self.y = list([0] * 1000)
        tau_buffer = self.y.copy()
        tau_d_buffer = self.y.copy()

        self.data_line1 = self.graphWidget.plot(t_buffer, tau_buffer, pen = red)
        self.data_line2 = self.graphWidget.plot(t_buffer, tau_d_buffer, pen = blue)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def update_plot_data(self):

        global tau_buffer
        global tau_d_buffer
        global t_buffer

        current_time = time.time() - start_time

        # Define the sinwave parameters and Computing the desired torque command
        amp   = 0.05
        cyti  = 5 # Cycle time (time in seconds to achieve one cycle)
        freq  = (2*math.pi)/cyti
        tau_d = amp*math.sin(current_time*freq)

        # Input the torque command
        axis.controller.input_torque = tau_d

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
        
        self.data_line1.setData(t_buffer, tau_buffer)
        self.data_line2.setData(t_buffer, tau_d_buffer)

app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec_())