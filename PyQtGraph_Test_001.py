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

# Parameters needed to avoid calibration
'''axis.current_state != AXIS_STATE_IDLE
odrv.erase_configuration()
odrv.reboot_odrive()
motor_config.phase_resistance = 0.113
motor_config.phase_inductance = 0.00005702
motor_config.phase_resistance_valid = True
motor_config.phase_inductance_valid = True
odrv.save_configuration()
odrv.reboot()'''

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
motor_config.calibration_current = 4
motor_config.resistance_calib_max_voltage = 2
motor_config.current_soft_max = 0.75 * Peak_current
motor_config.current_hard_max = 0.9 * Peak_current
motor_config.direction = 1
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
axis.controller.config.vel_limit = 20
axis.controller.config.vel_limit_tolerance = 1.5
axis.config.torque_soft_min = -torque_lim
axis.config.torque_soft_max = torque_lim

# Encoder configuration [Encoder]
axis.config.load_encoder = 4
axis.config.load_encoder = 10
axis.config.commutation_encoder = 10
#odrv.save_configuration()
#axis.requested_state = 7

'''# Skipping calibration
motor_config.phase_resistance = 0.117
motor_config.phase_inductance = 0.00005702
motor_config.phase_resistance_valid = True
motor_config.phase_inductance_valid = True'''

#odrv.save_configuration()

'''axis.requested_state = 7
while axis.current_state != 1:
        time.sleep(0.1)'''

# Running the calibration
calibration =  False
if calibration == True:
    print("Starting calibration...")
    axis.requested_state = 3
    while axis.current_state != 1:
        time.sleep(0.1)

# Activating the close loop control mode
axis.requested_state = 8

'''# This function is called periodically from FuncAnimation
def animate(i, t_vec, V_vec, tau_vec, tau_d_vec, I_vec, tdata_prev):
    # Computing the elapsed time
    t = time.time()
    t_data = round(t - t_0, 2)

    # Define the sinwave parameters and Computing the desired torque command
    amp   = 0.05
    cyti  = 5 # Cycle time (time in seconds to achieve one cycle)
    freq  = (2*math.pi)/cyti
    tau_d = amp*math.sin(t_data*freq)

    # Input the torque command
    axis.controller.input_torque = tau_d

    # Gathering the sensed data
    V   = odrv.vbus_voltage # Read the Voltage on the DC bus as measured by the ODrive.
    I   = axis.motor.foc.Iq_measured # Current in A that is responsible of the torque
    tau = axis.motor.torque_estimate # Torque estimate in Nm (based on the toque constant)

    sensor_data = {
        "time": t_data,
        "tau_d": tau_d,
        "tau": tau,
        "current": I,
        "bat_volt": V}

    if tdata_prev != t_data:
        with open(csv_file_name, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames = data_names)
            writer.writerow(sensor_data)

    # Add x and y to lists
    t_vec.append(str(t_data))
    V_vec.append(V)
    tau_vec.append(tau)
    tau_d_vec.append(tau_d)
    I_vec.append(I)

    # Limit x and y lists to 30 items
    samples = 30
    t_vec = t_vec[-samples:]
    V_vec = V_vec[-samples:]
    tau_vec = tau_vec[-samples:]
    tau_d_vec = tau_d_vec[-samples:]
    I_vec = I_vec[-samples:]

    # Draw x and y lists
    subplt_1.clear()
    subplt_1.plot(t_vec, V_vec)

    subplt_2.clear()
    subplt_2.plot(t_vec, tau_vec)
    subplt_2.plot(t_vec, tau_d_vec)

    subplt_3.clear()
    subplt_3.plot(t_vec, I_vec)

    # Format plot
    subplt_1.set(title = "Voltage in the BUS (from battery)",
                 ylabel = "Voltage [V]",
                 xticks = "")
    subplt_2.set(title = "Motor's Torque",
                 ylabel = "[Nm]",
                 xticks = "")
    subplt_3.set(title = "Current",
                 ylabel = "[A]")
    plt.xticks(rotation=45, ha='right')

    tdata_prev = t_data

# Setting the initial position of the shaft as zero
axis.set_abs_pos(0) # set as zero the initial position of the motor https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html#ODrive.Mapper.set_abs_pos



# Create figure for plotting
fig = plt.figure()
subplt_1 = fig.add_subplot(3, 1, 1)
subplt_2 = fig.add_subplot(3, 1, 2)
subplt_3 = fig.add_subplot(3, 1, 3)
t_vec = [] 
V_vec = []
tau_vec = []
tau_d_vec = []
I_vec = []

# Setup the initial time
t_0 = time.time()
tdata_prev = 0

csv_file_name = time.strftime("%Y-%m-%d_%H-%M-%S") + ".csv"
data_names = ["time", "tau_d", "tau", "current", "bat_volt"]

# Create the CSV file and write the header
with open(csv_file_name, mode="w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames = data_names)
    writer.writeheader()

ani = animation.FuncAnimation(fig, animate, fargs=(t_vec, V_vec, tau_vec, tau_d_vec, I_vec, tdata_prev), interval = 10)
plt.show()'''

# Data buffers
time_buffer = []
torque_buffer = []
current_buffer = []

start_time = time.time()
color = pg.mkPen(color=(255, 0, 0))

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        current_time = time.time() - start_time
        time_buffer.append(current_time)
        torque_buffer.append(axis.motor.torque_estimate)
        current_buffer.append(axis.motor.foc.Iq_measured)

        #torque_plot.setData(time_buffer, torque_buffer)
        #current_plot.setData(time_buffer, current_buffer)

        #self.x = list(range(100))  # 100 time points
        #self.y = [randint(0,100) for _ in range(100)]  # 100 data points

        self.graphWidget.setBackground('w')

        #color = pg.mkPen(color=(255, 0, 0))
        self.data_line =  self.graphWidget.plot(time_buffer, torque_buffer, pen=color)
        # ... init continued ...
        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def update_plot_data(self):

        current_time = time.time() - start_time

        '''self.x = self.x[1:]  # Remove the first y element.
        self.x.append(self.x[-1] + 1)  # Add a new value 1 higher than the last.

        self.y = self.y[1:]  # Remove the first
        self.y.append( randint(-100,100))  # Add a new random value.'''

        # Define the sinwave parameters and Computing the desired torque command
        amp   = 0.05
        cyti  = 5 # Cycle time (time in seconds to achieve one cycle)
        freq  = (2*math.pi)/cyti
        tau_d = amp*math.sin(current_time*freq)

        # Input the torque command
        axis.controller.input_torque = tau_d

        time_buffer.append(current_time)
        torque_buffer.append(axis.motor.torque_estimate)
        current_buffer.append(axis.motor.foc.Iq_measured)

        self.data_line =  self.graphWidget.plot(time_buffer, torque_buffer, pen=color)


app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec_())