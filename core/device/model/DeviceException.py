class DeviceException(Exception):
	pass

class requiresWIFISettings(DeviceException):
	super().__init__(f'This device type needs wifi settings!')


class maxDeviceOfTypeReached(DeviceException):
	def __init__(self, maxAmount: int):
		super().__init__(f'Maximal amount of {maxAmount} devices already reached')
		self.maxAmount = maxAmount


class maxDevicePerLocationReached(DeviceException):
	def __init__(self, maxAmount: int):
		super().__init__(f'Maximal amount of {maxAmount} devices in that location already reached')
		self.maxAmount = maxAmount
