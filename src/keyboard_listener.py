#!/usr/bin/env python3

from collections import defaultdict

from pynput.keyboard import Listener

class KeyboardListener:
	def __init__(self):
		self.keys = defaultdict(bool)
		self.listener = Listener(
			on_press=self.on_press,
			on_release=self.on_release
		)

	def on_press(self, key):
		try:
			self.keys[key.char] = True
		except AttributeError:
			keyname = str(key).split('.')[1]
			self.keys[keyname] = True
			pass

	def on_release(self, key):
		try:
			self.keys[key.char] = False
		except AttributeError:
			keyname = str(key).split('.')[1]
			self.keys[keyname] = False
			pass

	def start(self):
		self.listener.start()

	def stop(self):
		self.listener.stop()

if __name__ == '__main__':
	listener = KeyboardListener()
	listener.start()
	while True:
		print(listener.keys)
