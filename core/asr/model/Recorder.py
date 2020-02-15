import paho.mqtt.client as mqtt
import struct

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class Recorder(ProjectAliceObject):

	def __init__(self, session: DialogSession = None):
		super().__init__()
		self._session = session
		self._recording = False
		self._buffer = list()
		self._n = 0


	def __enter__(self):
		return self


	def __exit__(self, exc_type, exc_val, exc_tb):
		return True


	@property
	def session(self) -> DialogSession:
		return self._session


	@property
	def isRecording(self) -> bool:
		return self._recording


	def onStartListening(self, session: DialogSession):
		self.MqttManager.mqttClient.subscribe(constants.TOPIC_AUDIO_FRAME.format(session.siteId))
		self._recording = True


	def onSessionError(self, session: DialogSession):
		self.stopRecording()


	def stopRecording(self):
		self._recording = False
		self.MqttManager.mqttClient.unsubscribe(constants.TOPIC_AUDIO_FRAME.format(self._session.siteId))


	def getFrame(self, index: int = 0) -> bytes:
		try:
			return self._buffer[index]
		except:
			return b''


	def onAudioFrame(self, message: mqtt.MQTTMessage):
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
					self._buffer.append(message.payload[chunkOffset:chunkOffset + subChunk2Size])

				chunkOffset = chunkOffset + subChunk2Size + 8

		except Exception as e:
			self.logError(f'Error recording user speech: {e}')
