#  Copyright (c) 2021
#
#  This file, PorcupineWakeword.py, is part of Project Alice.
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
import queue
import struct
import wave
from typing import Generator

import pyaudio
from paho.mqtt.client import MQTTMessage

from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.voice.model.WakewordEngine import WakewordEngine


try:
	import pvporcupine
except ModuleNotFoundError:
	pass  # Will auto install


class PorcupineWakeword(WakewordEngine):
	NAME = 'Porcupine'
	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'pvporcupine==1.7.0'
		}
	}


	def __init__(self):
		super().__init__()
		self._working = self.ThreadManager.newEvent('ListenForWakeword')
		self._buffer = queue.Queue()
		self._hotwordThread = None

		try:
			self._handler = pvporcupine.create(keywords=['porcupine', 'bumblebee', 'terminator', 'blueberry'])
			with self.Commons.shutUpAlsaFFS():
				self._audio = pyaudio.PyAudio()
		except:
			self._enabled = False


	def onBooted(self):
		super().onBooted()
		if self._enabled:
			self._working.set()
			self._hotwordThread = self.ThreadManager.newThread(name='HotwordThread', target=self.worker)


	def onStop(self):
		super().onStop()
		if self._enabled:
			self._working.clear()
			self._buffer = queue.Queue()


	def onHotwordToggleOff(self, deviceUid: str):
		if self._enabled:
			self._working.clear()
			self._buffer = queue.Queue()


	def onHotwordToggleOn(self, deviceUid: str):
		if self._enabled:
			self._working.set()
			self._buffer = queue.Queue()
			self._hotwordThread = self.ThreadManager.newThread(name='HotwordThread', target=self.worker)


	def onAudioFrame(self, message: MQTTMessage, deviceUid: str):
		if not self.enabled or not self._working.is_set():
			return

		with io.BytesIO(message.payload) as buffer:
			try:
				with wave.open(buffer, 'rb') as wav:
					frame = wav.readframes(self.AudioServer.FRAMES_PER_BUFFER)
					while frame:
						self._buffer.put(frame)
						frame = wav.readframes(self.AudioServer.FRAMES_PER_BUFFER)

			except Exception as e:
				self.logError(f'Error recording audio frame: {e}')


	def worker(self):
		while True:
			stream = self.audioStream()
			for data in stream:
				if not self._working.is_set():
					break

				pcm = struct.unpack_from('h' * self._handler.frame_length, data)
				result = self._handler.process(pcm)
				if result is not None and result > -1:
					self.logDebug('Detected wakeword')
					self.MqttManager.publish(
						topic=constants.TOPIC_HOTWORD_DETECTED.format('default'),
						payload={
							'siteId'            : self.DeviceManager.getMainDevice().uid,
							'modelId'           : f'porcupine_{result}',
							'modelVersion'      : self._handler.version,
							'modelType'         : 'universal',
							'currentSensitivity': self.ConfigManager.getAliceConfigByName('wakewordSensitivity')
						}
					)
					return


	def audioStream(self) -> Generator:
		while self._working.is_set():
			chunk = self._buffer.get()
			if not chunk:
				return

			data = [chunk]
			size = len(chunk)

			while self._working and size < 1024:
				try:
					chunk = self._buffer.get(block=True)
					if not chunk or not self._working:
						return
					size += len(chunk)
					data.append(chunk)
				except queue.Empty:
					break

			yield b''.join(data)
