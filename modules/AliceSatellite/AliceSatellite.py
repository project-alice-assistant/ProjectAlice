from core.base.SuperManager import SuperManager
from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession


class AliceSatellite(Module):
	_INTENT_TEMPERATURE = Intent('GetTemperature')
	_INTENT_HUMIDITY = Intent('GetHumidity')
	_INTENT_CO2 = Intent('GetCo2Level')
	_INTENT_PRESSURE = Intent('GetPressure')

	_FEEDBACK_SENSORS = 'projectalice/devices/alice/sensorsFeedback'
	_DEVICE_DISCONNECTION = 'projectalice/devices/alice/disconnection'


	def __init__(self):
		self._SUPPORTED_INTENTS = [
			self._FEEDBACK_SENSORS,
			self._INTENT_TEMPERATURE,
			self._INTENT_HUMIDITY,
			self._INTENT_CO2,
			self._INTENT_PRESSURE,
			self._DEVICE_DISCONNECTION
		]

		self._temperatures = dict()
		self._sensorReadings = dict()

		self.ProtectedIntentManager.protectIntent(self._FEEDBACK_SENSORS)
		self.ProtectedIntentManager.protectIntent(self._DEVICE_DISCONNECTION)

		super().__init__(self._SUPPORTED_INTENTS)


	def onBooted(self):
		confManager = SuperManager.getInstance().configManager
		if confManager.configAliceExists('onReboot') and confManager.getAliceConfigByName('onReboot') == 'greetAndRebootModules':
			self.restartDevice()


	def onSleep(self):
		self.broadcast('projectalice/devices/sleep')


	def onWakeup(self):
		self.broadcast('projectalice/devices/wakeup')


	def onGoingBed(self):
		self.broadcast('projectalice/devices/goingBed')


	def onFullMinute(self):
		self.getSensorReadings()


	def onMessage(self, intent: str, session: DialogSession) -> bool:
		if not self.filterIntent(intent, session):
			return False

		sessionId = session.sessionId
		siteId = session.siteId
		slots = session.slots

		if 'Place' in slots:
			place = slots['Place']
		else:
			place = siteId

		if intent == self._INTENT_TEMPERATURE:
			temp = self.getSensorValue(place, 'temperature')

			if temp == 'undefined':
				return False

			if place != siteId:
				self.endDialog(sessionId, self.randomTalk('temperaturePlaceSpecific').format(place, temp.replace('.0', '')))
			else:
				self.endDialog(sessionId, self.randomTalk('temperature').format(temp.replace('.0', '')))

			return True

		elif intent == self._INTENT_HUMIDITY:
			humidity = self.getSensorValue(place, 'humidity')

			if humidity == 'undefined':
				return False
			else:
				humidity = int(round(float(humidity), 0))

			if place != siteId:
				self.endDialog(sessionId, self.randomTalk(text='humidityPlaceSpecific', replace=[place, humidity]))
			else:
				self.endDialog(sessionId, self.randomTalk(text='humidity', replace=[humidity]))

			return True

		elif intent == self._INTENT_CO2:
			co2 = self.getSensorValue(place, 'gas')

			if co2 == 'undefined':
				return False

			if place != siteId:
				self.endDialog(sessionId, self.TalkManager.randomTalk('co2PlaceSpecific').format(place, co2))
			else:
				self.endDialog(sessionId, self.TalkManager.randomTalk('co2').format(co2))

			return True

		elif intent == self._INTENT_PRESSURE:
			pressure = self.getSensorValue(place, 'pressure')

			if pressure == 'undefined':
				return False
			else:
				pressure = int(round(float(pressure), 0))

			if place != siteId:
				self.endDialog(sessionId, self.randomTalk(text='pressurePlaceSpecific', replace=[place, pressure]))
			else:
				self.endDialog(sessionId, self.randomTalk(text='pressure', replace=[pressure]))

			return True

		elif intent == self._FEEDBACK_SENSORS:
			payload = session.payload
			if 'data' in payload:
				self._sensorReadings[siteId] = payload['data']
			return True

		elif intent == self._DEVICE_DISCONNECTION:
			payload = session.payload
			if 'uid' in payload:
				self.DeviceManager.deviceDisconnecting(payload['uid'])

		return False


	def getSensorReadings(self):
		self.broadcast('projectalice/devices/alice/getSensors')


	def temperatureAt(self, siteId: str) -> str:
		return self.getSensorValue(siteId, 'temperature')


	def getSensorValue(self, siteId: str, value: str) -> str:
		if siteId not in self._sensorReadings.keys():
			return 'undefined'

		data = self._sensorReadings[siteId]
		if value in data:
			ret = data[value]
			return ret
		else:
			return 'undefined'


	def restartDevice(self):
		devices = self.DeviceManager.getDevicesByType(deviceType=self.name, connectedOnly=True, onlyOne=False)
		if not devices:
			return

		for device in devices:
			self.publish(topic='projectalice/devices/restart', payload={'uid': device.uid})
