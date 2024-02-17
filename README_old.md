# Torque control for a BLDC motor

Strongly recomend to check the basic documentation before anything

- General: https://docs.odriverobotics.com/v/latest/guides/getting-started.html
- Python package: https://docs.odriverobotics.com/v/latest/guides/python-package.html

The "ODrive_torque_Ctrl.py" file contains the code to perform torque control of a BLDC motor using a ODrive board.

## Hardware description

![Hardware setup 1](ODrive_BLDC_01.png)
![Hardware setup 2](ODrive_BLDC_02.png)

### Motor (Brushless DC)

T-Motor MN4006-23 KV: 380

https://store.tmotor.com/goods-440-Antigravity+MN4006+KV380+-+2PCSSET.html

### Board

ODrive S1

https://odriverobotics.com/shop/odrive-

https://docs.odriverobotics.com/v/latest/hardware/s1-datasheet.html

### Battery (LiPo)

HRB 6S 22.2V 1800mAh 50C

https://hrb-power.com/products/hrb-6s-22-2v-1800mah-100c-lipo-battery-xt60

### USB Isolator v3.6

https://odriverobotics.com/shop/usb-isolator

### Brake resistor

2 Ohm, 50W

https://odriverobotics.com/shop/set-of-8-brake-resistors

### Motor mounting plate

https://odriverobotics.com/shop/pancake-motor-plate

# First connection

Strongly recommend to use the ODrive GUI before coding

https://gui.odriverobotics.com/configuration

Input the required parameters in all of the sections
- Power source (related to the specs of the battery)
- Motor
- Encoder (we are using the onboard encoder)
- Control mode (try first the recommendations in there)

Then:

1. Erase old configuration
2. Apply new configuration (will upload the parameters you entered before)
3. Save to non-volatile memory
4. Calibrate (must run the calibration the first time you connect)

After these, you can now go to the Dashboard and see real-time data (angular position, velocity, and current).

You can try different control modes (position, velocity, and torque) to familiarize yourself with how the motor reacts to the input commands.

# The Python code

First, install the ODrive tool API (https://docs.odriverobotics.com/v/latest/interfaces/odrivetool.html#install-odrivetool)
~~~ bash
pip install --upgrade odrive
~~~
Once the odrive tool is installed, you can import it into your python code:
~~~ bash
import odrive
~~~
Then, you must use the predefined commands to perform any operation/action with the ODrive board and the motor.

The whole list and description of commands can be found in https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html

## Setting up the parameters (code)
A crucial part of properly controlling the motor is to define accurately the parameters of the whole system.
These parameters are comming from the specs and charactaristics of the employed hawrdware.
Besides, will help to avoid damaging the battery, motor an ODrive board.

### 1. Power source

The `bat_capacity`, `bat_discharge_rate`, and `bat_n_cells` are constants defined by the characteristics of the employed battery

~~~ bash
# HRB LiPo Battery | 1800 mAh | 22.2 v | 6S | 50C
# Voltage Limits
bat_capacity = 1.8 # in Ah = 1800 mAh
bat_discharge_rate = 50 # 50C
bat_n_cells = 6 # 6S
odrv.config.dc_bus_undervoltage_trip_level = 3.3 * bat_n_cells
odrv.config.dc_bus_overvoltage_trip_level = 4.25 * bat_n_cells

# Current Limits
odrv.config.dc_max_positive_current = bat_capacity * bat_discharge_rate # max battery discharge current
odrv.config.dc_max_negative_current = -odrv.config.dc_max_positive_current # max battery charging current

# Usage of Brake resistor
odrv.config.brake_resistor0.enable = True # The 50W2RJ resistor (huge black resistor) 
odrv.config.brake_resistor0.resistance = 2 # The resistance of the 50W2RJ resistor (huge black resistor)
~~~

### 2. Motor

The `KV_rating` and `Peak_current` constants were defined based on the data sheet of the motor.
The value of `motor_config.motor_type` was defined based on the documentation of the ODrive tool API.
In addition, all the other parameter correspond to chracteristics of the motor.

You can modify the `0.65` and `0.85` values in `motor_config.current_soft_max` and `motor_config.current_hard_max` to be less conservative.
However, you should start with this conservative selection to avoid damaging the motor due to overcurrent.

~~~ bash
# T-Motor BLDC Motor | MN4006-23 | KV:380
KV_rating = 380
Peak_current = 16 # A
motor_config.motor_type = 0 # https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html#ODrive.MotorType
motor_config.pole_pairs = 12 # Number of magnet poles in the rotor, divided by two.
motor_config.torque_constant = 8.27/KV_rating
motor_config.calibration_current = 6
motor_config.current_soft_max = 0.65 * Peak_current
motor_config.current_hard_max = 0.85 * Peak_current
~~~

### 3. Encoder

Since the onboard encoder is used, this is the appropiate selction based on the documentation of the ODrive tool API.

~~~ bash
odrv.axis0.config.load_encoder = 13 # https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html#ODrive.EncoderId
odrv.axis0.config.commutation_encoder = 13
~~~

### 4. Control mode (Torque control)

First, we define in `torque_lim` the maximum torque to be produced by the motor.
The torque control that ODrive provides its based on current i.e., the output torque is the product of the current (`axis.motor.foc.Iq_measured`) and the torque constant (`motor_config.torque_constant`).
Therefore, to guarantee the safety of the motor, we define the maximun torque as a funtion of the maximum current of the motor (`motor_config.current_soft_max`).

The `motor_config.torque_constant` and `motor_config.current_soft_max` parameters where defined before (motor configuration).

The values of `ctrl_config.control_mode` and `ctrl_config.input_mode` were defined based on the documentation of the ODrive tool API.

~~~ bash
####### Setting up the control mode (position, velocity, torque) [Control mode] #######
torque_lim = motor_config.current_soft_max * motor_config.torque_constant # Max allowed torque in Nm
ctrl_config.control_mode = 1 # https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html#ODrive.Controller.ControlMode
ctrl_config.input_mode = 1 # https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html#ODrive.Controller.InputMode
axis.controller.config.vel_limit = 20
axis.controller.config.vel_limit_tolerance = 1.5
axis.config.torque_soft_min = -torque_lim
axis.config.torque_soft_max = torque_lim

# Activating the close loop control mode
axis.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
~~~

## Sending torque commands (code)

Once all the setup parameters are defined we only need to send torque commands and the inner control loop will handle everything to reach the desired command.

It is just matter of put the following code in a loop (see `ODrive_torque_Ctrl.py`).

~~~ bash
# Computing the elapsed time
t = time.time()
t_data = round(t - t_0, 2)

# Define the sinwave parameters
amp   = 0.2
cycle = 5
freq  = (2*math.pi)/cycle

# Computing the desired torque command
tau_d = amp*math.sin(t*freq)

# Input the torque command
axis.controller.input_torque = -tau_d
~~~

The ODrive tool API instruction to send torque commands is `axis.controller.input_torque = -tau_d`.