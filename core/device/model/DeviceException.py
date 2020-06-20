from core.ProjectAliceExceptions import ProjectAliceException

class DeviceException(ProjectAliceException):
	def __init__(self, message: str = None, status: int = None, context: list = None):
		super().__init__(message, status, context)


class RequiresWIFISettings(DeviceException):
	def __init__(self):
		super().__init__(f'This device type needs wifi settings!')


class MaxDeviceOfTypeReached(DeviceException):
	def __init__(self, maxAmount: int):
		super().__init__(f'Maximal amount of {maxAmount} devices already reached')
		self.maxAmount = maxAmount


class MaxDevicePerLocationReached(DeviceException):
	def __init__(self, maxAmount: int):
		super().__init__(f'Maximal amount of {maxAmount} devices in that location already reached')
		self.maxAmount = maxAmount


class RequiresGuiSettings(DeviceException):
	def __init__(self):
		super().__init__(f'This device type needs additional information in the my home web interface.')


class DeviceNotPaired(DeviceException):
	def __init__(self):
		super().__init__(f'This device is currently not paired.')
