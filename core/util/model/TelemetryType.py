#  Copyright (c) 2021
#
#  This file, TelemetryType.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:48 CEST

from enum import Enum

class TelemetryType(Enum):
	TEMPERATURE = 'temperature'
	TARGETTEMPERATURE = 'targetTemperature'
	PRESSURE = 'pressure'
	HUMIDITY = 'humidity'
	LIGHT = 'light'
	GAS = 'gas'
	AIR_QUALITY = 'airQuality'
	UV_INDEX = 'uvIndex'
	NOISE = 'noise'
	CO2 = 'co2'
	RAIN = 'rain'
	SUM_RAIN_1 = 'sumRain1'
	SUM_RAIN_24 = 'sumRain24'
	WIND_STRENGTH = 'windStrength'
	WIND_ANGLE = 'windAngle'
	GUST_STRENGTH = 'gustStrength'
	GUST_ANGLE = 'gustAngle'
	DEWPOINT = 'dewPoint'
	BATTERY = 'battery'
	VOLTAGE = 'voltage'
	CONTACT = 'contact'
	LINKQUALITY = 'linkquality'
	LATENCY = 'latency'
	PACKET_LOSS = 'packetLoss'
	STATE = 'state'
	MODE = 'mode'


	@classmethod
	def _missing_(cls, value):
		""" synonyms for different values """
		if value in ['local_temperature']:
			return TelemetryType.TEMPERATURE
		if value in ['current_heating_setpoint']:
			return TelemetryType.TARGETTEMPERATURE
		if value in ['system_mode']:
			return TelemetryType.MODE
