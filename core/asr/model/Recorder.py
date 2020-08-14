import queue
import threading
import wave
from typing import Optional

import io
import paho.mqtt.client as mqtt

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession


class Recorder(ProjectAliceObject):

	def __init__(self, timeoutFlag: threading.Event, user: str, siteId: str):
		super().__init__()
		self._user = user,
		self._siteId = siteId
		self._recording = False
		self._timeoutFlag = timeoutFlag
		self._buffer = queue.Queue()


	def __enter__(self):
		self.startRecording()
		return self


	def __exit__(self, excType, excVal, excTb):
		self.stopRecording()


	@property
	def isRecording(self) -> bool:
		return self._recording


	def onSessionError(self, session: DialogSession):
		self.stopRecording()


	def startRecording(self):
		self._recording = True


	def stopRecording(self):
		self._recording = False
		self._buffer.put(None)


	def onAudioFrame(self, message: mqtt.MQTTMessage, siteId: str):
		with io.BytesIO(message.payload) as buffer:
			try:
				with wave.open(buffer, 'rb') as wav:
					frame = wav.readframes(512)
					while frame:
						self._buffer.put(frame)

						if self.ConfigManager.getAliceConfigByName('recordAudioAfterWakeword'):
							self.AudioServer.recordFrame(siteId, frame)

						frame = wav.readframes(512)

			except Exception as e:
				self.logError(f'Error recording user speech: {e}')


	def __iter__(self):
		while self._recording:
			if self._timeoutFlag.isSet():
				return

			chunk = self._buffer.get()

			if not chunk:
				break

			yield chunk

		# Empty the buffer
		data = list()
		while not self._buffer.empty():
			chunk = self._buffer.get(block=False)
			if not chunk or not self._recording:
				break

			data.append(chunk)

		yield b''.join(data)


	def audioStream(self) -> Optional[bytes]:
		while not self._buffer.empty() or self._recording:
			if self._timeoutFlag.isSet():
				return

			chunk = self._buffer.get()
			if not chunk:
				return

			data = [chunk]

			while self._recording:
				try:
					chunk = self._buffer.get(block=False)
					if not chunk or not self._recording:
						return

					data.append(chunk)
				except queue.Empty:
					break

			yield b''.join(data)
