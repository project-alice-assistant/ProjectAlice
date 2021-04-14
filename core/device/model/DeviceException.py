#  Copyright (c) 2021
#
#  This file, DeviceException.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:46 CEST

from core.ProjectAliceExceptions import ProjectAliceException

class DeviceException(ProjectAliceException):
	def __init__(self, message: str = None, status: int = None, context: list = None):
		super().__init__(message, status, context)


class DeviceTypeUndefined(DeviceException):
	def __init__(self, deviceName: str):
		super().__init__(f'The device {deviceName} has no defined type')


class RequiresWIFISettings(DeviceException):
	def __init__(self):
		super().__init__('This device type needs wifi settings!')


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
