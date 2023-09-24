#!/usr/bin/env python3

from math import copysign
from threading import Lock

import rospy
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse

from keyboard_listener import KeyboardListener

### helpers ##################################################################

def clamp(value: float, lower: float, upper: float) -> float:
	return min(upper, max(value, lower))

### main #####################################################################

def main():
	Keyboard().loop()

class Keyboard:
	def __init__(self):

		rospy.init_node("keyboard_input")

		### local variables ##################################################

		self.frequency = rospy.get_param("~frequency")
		self.turbo_multiplier = rospy.get_param("~turbo_multiplier")
		self.base_multiplier = rospy.get_param("~base_multiplier")

		self.min_linear_speed = rospy.get_param("~min_linear_speed")
		self.max_linear_speed = rospy.get_param("~max_linear_speed")
		self.min_angular_speed = rospy.get_param("~min_angular_speed")
		self.max_angular_speed = rospy.get_param("~max_angular_speed")

		self.enabled = rospy.get_param("~enabled_on_start")  # whether or not to publish cmd_vel
		self.enabled_lock = Lock()

		self.drive_direction_correction = 1
		self.drive_direction_correction_lock = Lock()

		self.car_style_turning = False
		self.car_style_turning_lock = Lock()

		### start keyboard listener ##########################################

		self.listener = KeyboardListener()
		self.listener.start()
		self.keys = self.listener.keys

		### connect to ROS ###################################################

		cmd_vel_topic = rospy.get_param("~cmd_vel_topic")
		selected_mode_topic = rospy.get_param("~selected_mode_topic")
		enabled_service = rospy.get_param("~enabled_service")
		drive_forward_service = rospy.get_param("~drive_forward_service")
		car_style_turning_service = rospy.get_param("~car_style_turning_service")

		self.cmd_vel_pub = rospy.Publisher(cmd_vel_topic, Twist, queue_size=1)
		self.selected_mode_pub = rospy.Publisher(selected_mode_topic, String, queue_size=1)
		self.enabled_srv = rospy.Service(enabled_service, SetBool, self.enabled_callback)
		self.drive_forward_srv = rospy.Service(drive_forward_service, SetBool, self.drive_direction_callback)
		self.turning_style_srv = rospy.Service(car_style_turning_service, SetBool, self.turning_style_callback)

		### end init #########################################################

	def enabled_callback(self, bool: SetBoolRequest) -> SetBoolResponse:
		with self.enabled_lock:
			self.enabled = bool.data
		response = SetBoolResponse()
		response.success = True
		response.message = "Updated keyboard_input enable status"
		return response
	
	def drive_direction_callback(self, drive_forward_request: SetBoolRequest) -> SetBoolResponse:
		if drive_forward_request.data:
			drive_direction_correction = 1
			drive_desc = 'forward'
		else:
			drive_direction_correction = -1
			drive_desc = 'backward'

		with self.drive_direction_correction_lock:
			self.drive_direction_correction = drive_direction_correction

		response = SetBoolResponse()
		response.success = True
		response.message = f"Driving {drive_desc}"
		return response
	
	def turning_style_callback(self, turning_style_request: SetBoolRequest) -> SetBoolResponse:
		with self.car_style_turning_lock:
			self.car_style_turning = turning_style_request.data

		response = SetBoolResponse()
		response.success = True
		response.message = f"Car style turning set to {turning_style_request.data}"
		return response

	def keyboard_to_cmd_vel(self):
		# key switches
		teleop_switch = self.keys['t']
		autonomy_switch = self.keys['p']
		return_home_switch = self.keys['h']
		takeoff_switch = self.keys['o']
		land_switch = self.keys['l']
		emergency_stop_switch = self.keys['esc']
		turbo_switch = self.keys['ctrl']
		forward = self.keys['w'] or self.keys['up']
		backward = self.keys['s'] or self.keys['down']
		left = self.keys['a'] or self.keys['left']
		right = self.keys['d'] or self.keys['right']
		down = self.keys['shift'] or self.keys['shift_r']
		up = self.keys['space']

		### update user mode selection
		if teleop_switch:
			self.selected_mode_pub.publish(String("teleop"))
		elif autonomy_switch:
			self.selected_mode_pub.publish(String("autonomy"))
		elif return_home_switch:
			self.selected_mode_pub.publish(String("return_home"))
		elif takeoff_switch:
			self.selected_mode_pub.publish(String("takeoff"))
		elif land_switch:
			self.selected_mode_pub.publish(String("land"))
		elif emergency_stop_switch:
			self.selected_mode_pub.publish(String("emergency_stop"))

		### translate keyboard to cmd_vel ###
		if not self.enabled:
			return

		linear_x = forward - backward
		linear_z = up - down
		angular = left - right
		with self.car_style_turning_lock:
			if self.car_style_turning:
				angular = angular * copysign(1, linear_x)

		# drive direction correction
		linear_x = linear_x * self.drive_direction_correction
		# angular = angular * self.drive_direction_correction # not needed because of car style turning

		# scaling
		multiplier = self.turbo_multiplier if turbo_switch else self.base_multiplier
		linear_x_scale = abs(self.max_linear_speed if linear_x >= 0 else self.min_linear_speed) * multiplier
		linear_z_scale = abs(self.max_linear_speed if linear_x >= 0 else self.min_linear_speed) * multiplier
		angular_scale = abs(self.max_angular_speed if angular >= 0 else self.min_angular_speed) * multiplier

		# scale cmd_vel and publish
		cmd_vel = Twist()
		cmd_vel.linear.x = clamp(linear_x * linear_x_scale, self.min_linear_speed, self.max_linear_speed)
		cmd_vel.linear.z = clamp(linear_z * linear_z_scale, self.min_linear_speed, self.max_linear_speed)
		cmd_vel.angular.z = clamp(angular * angular_scale, self.min_angular_speed, self.max_angular_speed)
		self.cmd_vel_pub.publish(cmd_vel)

	def loop(self):
		rate = rospy.Rate(self.frequency)
		while not rospy.is_shutdown():
			self.keyboard_to_cmd_vel()
			rate.sleep()

if __name__ == "__main__":
	main()
