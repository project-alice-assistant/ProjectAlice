import queue
import wave
from typing import Optional

import io
import pyaudio
import struct
from paho.mqtt.client import MQTTMessage

from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.voice.model.WakewordEngine import WakewordEngine

try:
	import pvporcupine
except ModuleNotFoundError:
	pass # Will autoinstall

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


	def onHotwordToggleOff(self, siteId: str, session: DialogSession):
		if self._enabled:
			self._working.clear()
			self._buffer = queue.Queue()


	def onHotwordToggleOn(self, siteId: str, session: DialogSession):
		if self._enabled:
			self._working.set()
			self._buffer = queue.Queue()
			self._hotwordThread = self.ThreadManager.newThread(name='HotwordThread', target=self.worker)


	def onAudioFrame(self, message: MQTTMessage, siteId: str):
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
							'siteId': self.ConfigManager.getAliceConfigByName('deviceName'),
							'modelId': f'porcupine_{result}',
							'modelVersion': self._handler.version,
							'modelType': 'universal',
							'currentSensitivity': self.ConfigManager.getAliceConfigByName('wakewordSensitivity')
						}
					)
					return


	def audioStream(self) -> Optional[bytes]:
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
