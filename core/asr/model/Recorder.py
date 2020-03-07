import queue
import threading
from typing import Optional

import paho.mqtt.client as mqtt
import struct

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession


class Recorder(ProjectAliceObject):

	def __init__(self, timeoutFlag: threading.Event):
		super().__init__()
		self._recording = False
		self._timeoutFlag = timeoutFlag
		self._buffer = queue.Queue()


	def __enter__(self):
		self.startRecording()
		return self


	def __exit__(self, exc_type, exc_val, exc_tb):
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


	def onAudioFrame(self, message: mqtt.MQTTMessage):
		if not self._recording:
			return

		try:
			riff, size, fformat = struct.unpack('<4sI4s', message.payload[:12])

			if riff != b'RIFF':
				self.logError('Frame parse error')
				return

			if fformat != b'WAVE':
				self.logError('Frame wrong format')
				return

			chunkOffset = 52
			while chunkOffset < size:
				subChunk2Id, subChunk2Size = struct.unpack('<4sI', message.payload[chunkOffset:chunkOffset + 8])
				chunkOffset += 8
				if subChunk2Id == b'data':
					self._buffer.put(message.payload[chunkOffset:chunkOffset + subChunk2Size])

				chunkOffset = chunkOffset + subChunk2Size + 8

		except Exception as e:
			self.logError(f'Error recording user speech: {e}')


	def __iter__(self):
		while not self._buffer.empty():
			yield self._buffer.get()


	def audioStream(self) -> Optional[bytes]:
		while not self._buffer.empty():
			if self._timeoutFlag.isSet():
				return

			chunk = self._buffer.get()
			if not chunk:
				return

			data = [chunk]

			while True:
				try:
					chunk = self._buffer.get(block=False)
					if not chunk:
						return

					data.append(chunk)
				except queue.Empty:
					break

			yield b''.join(data)
