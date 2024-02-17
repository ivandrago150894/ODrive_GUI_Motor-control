'''
=== ENTRY 2024/01/18 === THIS CODE IS RUNNIG BUT ONLY WORKS DOING THE CALIBRATION IN THE CODE

This code is a modifications of the not-running version of "PyQtGraph_Test_008.py".
In this code I'm trying to finally upload the configuration for the Motor, Encoder and ODrive
direclty from the code.

==> Now I found a way to reconnect the ODrive after erasing and saving the configuration.
    It works good to reconnect once the ODrive was lost.
    Even though the configuration ot seems to save, the calibration aknolege is not True,
    so I cannot send torque commands.

The following modifications has been made to the code:

1. The whole configuration of the actuator was added
2. try and except conditions were added to allow the reconnection of the ODrive

'''

import odrive # Import the ODrive API
from odrive.enums import *
import time
import datetime as dt
from math import *
import csv
from PyQt5 import QtWidgets, QtCore, QtGui
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QTabWidget, QGridLayout, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import sys

# Find the ODrive board connected to any serial port
odrv = odrive.find_any()

try:
    print('Starting configuration erase')
    odrv.erase_configuration()
except:
    time.sleep(1)
    odrv = odrive.find_any()
    print('Configuration erased Finished')
    try:
        print('Reboot started...')
        odrv.reboot()
    except:
        time.sleep(1)
        odrv         = odrive.find_any()
        axis         = odrv.axis0
        motor        = axis.motor
        motor_config = axis.config.motor
        ctrl_config  = axis.controller.config
        print('Reboot finished')

print('Updating the configuration')
####### CONFIGURATION OF THE ODrive BOARD [Power source] #######
# Voltage Limits
bat_capacity = 1.8 # in Ah = 1800 mAh
bat_discharge_rate = 50 # 50C
bat_n_cells = 6 # number of cells in series
odrv.config.dc_bus_undervoltage_trip_level = 3.3 * bat_n_cells
odrv.config.dc_bus_overvoltage_trip_level = 4.25 * bat_n_cells  

# Current Limits
odrv.config.dc_max_positive_current = bat_capacity * bat_discharge_rate # max battery discharge current
odrv.config.dc_max_negative_current = -odrv.config.dc_max_positive_current # max battery charging current

# Usage of Brake resistor
odrv.config.brake_resistor0.enable = True # The 50W2RJ resistor (huge black resistor) 
odrv.config.brake_resistor0.resistance = 2 # The resistance of the 50W2RJ resistor (huge black resistor)

####### SETTING THE MOTOR SPECS [Motor] #######
# T-Motor BLDC Motor MN4006-23 KV:380
KV_rating = 380
Peak_current = 16 # A
motor_config.motor_type = 0 # https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html#ODrive.MotorType
motor_config.pole_pairs = 12 # Number of magnet poles in the rotor, divided by two.
motor_config.torque_constant = 8.27/KV_rating
motor_config.calibration_current = 10
motor_config.resistance_calib_max_voltage = 5
motor_config.current_soft_max = 0.75 * Peak_current
motor_config.current_hard_max = 0.9 * Peak_current
#motor_config.direction = -1
motor_config.phase_resistance = 0.113
motor_config.phase_inductance = 0.00005702
motor_config.phase_resistance_valid = True
motor_config.phase_inductance_valid = True
''' Follow this recommendation
This should be set to less than (0.5 * vbus_voltage), but high enough to satisfy V=IR during motor calibration,
where I is config.calibration_current and R is config.phase_resistance

config.motor.resistance_calib_max_voltage > calibration_current * phase_resistance
config.motor.resistance_calib_max_voltage < 0.5 * vbus_voltage
'''

####### Setting up the control mode (position, velocity, torque) [Control mode] #######
torque_lim = motor_config.current_soft_max * motor_config.torque_constant # Max allowed torque in Nm
ctrl_config.control_mode = 1 # https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html#ODrive.Controller.ControlMode
ctrl_config.input_mode = 1 # https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html#ODrive.Controller.InputMode
axis.controller.config.vel_limit = 100
axis.controller.config.vel_limit_tolerance = 1.5
axis.config.torque_soft_min = -torque_lim
axis.config.torque_soft_max = torque_lim

# Encoder configuration [Encoder]
odrv.rs485_encoder_group0.config.mode = 4
axis.config.load_encoder = 10
axis.config.commutation_encoder = 10
print('Configuration done')

'''KV_rating = 380
motor_config.pole_pairs = 12 # Number of magnet poles in the rotor, divided by two.
motor_config.torque_constant = 8.27/KV_rating
motor_config.direction = 1
motor_config.phase_resistance = 0.113
motor_config.phase_inductance = 0.00005702
motor_config.phase_resistance_valid = True
motor_config.phase_inductance_valid = True'''

try:
    print('Saving configuration')
    odrv.save_configuration()
except:
    time.sleep(1)
    odrv         = odrive.find_any() # Find the ODrive board connected to any serial port
    print('Configuration saved')
    try:
        print('Reboot started...')
        odrv.reboot()
    except:
        time.sleep(1)
        odrv         = odrive.find_any()
        axis         = odrv.axis0
        motor        = axis.motor
        motor_config = axis.config.motor
        ctrl_config  = axis.controller.config
        print('Reboot finished')

print('Starting encoder calibration...')
axis.requested_state = 7
while axis.current_state != 1:
    time.sleep(0.1)
    print(axis.current_state)
print('Encoder calibration finished')

try:
    print('Saving configuration')
    odrv.save_configuration()
except:
    time.sleep(1)
    odrv         = odrive.find_any() # Find the ODrive board connected to any serial port
    print('Configuration saved')
    try:
        print('Reboot started...')
        odrv.reboot()
    except:
        time.sleep(1)
        odrv         = odrive.find_any()
        axis         = odrv.axis0
        motor        = axis.motor
        motor_config = axis.config.motor
        ctrl_config  = axis.controller.config
        print('Reboot finished')

motor_config.direction = -1
axis.set_abs_pos(0)
axis.requested_state = 8

win_size = 200 # Quantity of data points to be displayed in the GUI when real-time plotting
t_buffer       = list([0] * win_size)
tau_buffer     = t_buffer.copy()
tau_d_buffer   = t_buffer.copy()
current_buffer = t_buffer.copy()
voltage_buffer = t_buffer.copy()
pos_buffer     = t_buffer.copy()

red  = pg.mkPen(color=(255, 0, 0), width = 2)
blue = pg.mkPen(color=(0, 0, 255), width = 2)

LogginButton_Flag = False
TRefBox_Flag      = False
t_0   = 0
tau_d = 0

class MainWindow(QWidget):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        global t_buffer, tau_d_buffer, tau_buffer, current_buffer, voltage_buffer, pos_buffer,\
            t_0, t_minus_1,\
            tau_d,\
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

        # Initialization of variables
        self.timer = QtCore.QTimer()
        self.timer.setInterval(20) # Set the refresh time-rate for the plotted data in the GUI
        t_0 = time.time() # Set the initial tim
        t_minus_1 = t_0 # Time variable to ensure that no repeated data is ploted
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()
            
       
    def update_plot_data(self):
        global t_buffer, tau_d_buffer, tau_buffer, current_buffer, voltage_buffer, pos_buffer,\
            t_0, t_minus_1,\
            tau_d,\
            LogginButton_Flag, TRefBox_Flag,\
            csv_file_name, DataHeaders,\
            TRefBox_Command
        
        t = time.time() - t_0
                
        if t_minus_1 != t:
                       
            if TRefBox_Flag != False:
                tau_d = float(eval(TRefBox_Command))

            # Input the torque command
            axis.controller.input_torque = -tau_d
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

            if LogginButton_Flag == True:
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
    global LogginButton_Flag, LoggingButton, csv_file_name, DataHeaders
    LogginButton_Flag = True
    LoggingButton.setText("Logging data")
    LoggingButton.setStyleSheet("background-color : green")
    csv_file_name = "GUI_Logger_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".csv"
    DataHeaders = ["time", "tau_d", "tau", "current", "bat_volt", "ang_pos"]

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