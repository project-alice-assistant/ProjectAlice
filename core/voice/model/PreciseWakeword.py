#  Copyright (c) 2021
#
#  This file, PreciseWakeword.py, is part of Project Alice.
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

import io
import wave

from paho.mqtt.client import MQTTMessage

from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.voice.model.WakewordEngine import WakewordEngine


try:
	from precise_runner import PreciseEngine, PreciseRunner, ReadWriteStream
except ModuleNotFoundError:
	pass # Autoinstall

class PreciseWakeword(WakewordEngine):

	NAME = 'Precise'
	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'mycroft-precise==0.3.0'
		}
	}

	def __init__(self):
		super().__init__()
		self._hotwordThread = None

		try:
			self._stream = ReadWriteStream()
			self._handler = PreciseRunner(
				PreciseEngine(
					exe_file=f'{self.Commons.rootDir()}/venv/bin/precise-engine',
					model_file=f'{self.Commons.rootDir()}/trained/hotwords/mycroft-precise/athena.pb'
				),
				sensitivity=self.ConfigManager.getAliceConfigByName('wakewordSensitivity'),
				stream=self._stream,
				on_activation=self.hotwordSpotted
			)
		except:
			self._enabled = False


	def onBooted(self):
		super().onBooted()
		if self._enabled:
			if not self._handler:
				self.logWarning('Hotword engine failed to init')
			else:
				self._handler.start()


	def onStop(self):
		super().onStop()
		if self._handler:
			self._handler.stop()


	def hotwordSpotted(self):
		self.logDebug('Detected wakeword')
		self._handler.pause()

		self.MqttManager.publish(
			topic=constants.TOPIC_HOTWORD_DETECTED.format('default'),
			payload={
				'siteId'            : self.DeviceManager.getMainDevice().uid,
				'modelId'           : f'precise_athena',
				'modelVersion'      : '0.3.0',
				'modelType'         : 'universal',
				'currentSensitivity': self.ConfigManager.getAliceConfigByName('wakewordSensitivity')
			}
		)


	def onHotwordToggleOn(self, deviceUid: str, session: DialogSession):
		if self._enabled and self._handler:
			self._handler.start()


	def onAudioFrame(self, message: MQTTMessage, deviceUid: str):
		if not self.enabled or not self._handler or self._handler.is_paused or self._stream is None:
			return

		with io.BytesIO(message.payload) as buffer:
			try:
				with wave.open(buffer, 'rb') as wav:
					frame = wav.readframes(self.AudioServer.FRAMES_PER_BUFFER)
					while frame:
						self._stream.write(frame)
						frame = wav.readframes(self.AudioServer.FRAMES_PER_BUFFER)

			except Exception as e:
				self.logError(f'Error recording audio frame: {e}')
