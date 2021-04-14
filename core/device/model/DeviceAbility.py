#  Copyright (c) 2021
#
#  This file, DeviceAbility.py, is part of Project Alice.
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

from enum import IntFlag


class DeviceAbility(IntFlag):
	NONE = 1 << 0
	IS_CORE = 1 << 1
	IS_SATELITTE = 1 << 2
	CAPTURE_SOUND = 1 << 4
	PLAY_SOUND = 1 << 8
	DISPLAY = 1 << 16
	PHYSICAL_USER_INPUT = 1 << 32
	KEYBOARD = 1 << 64
	ALERT = 1 << 128
	NOTIFY = 1 << 256
