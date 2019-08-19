# -*- coding: utf-8 -*-

from enum import Enum

class TelemetryType(Enum):
	TEMPERATURE = 'temperature'
	PRESSURE = 'pressure'
	HUMIDITY = 'humidity'
	LIGHT = 'light'
	GAS = 'gas'
	AIR_QUALITY = 'airQuality'
	UV_INDEX = 'uvIndex'
	DECIBEL = 'decibel'

