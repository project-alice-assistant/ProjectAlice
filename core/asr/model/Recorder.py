import uuid
import wave
from pathlib import Path

import paho.mqtt.client as mqtt
import struct

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class Recorder(ProjectAliceObject):

	def __init__(self):
		super().__init__()
		self._filepath = Path(f'/tmp/{uuid.uuid4()}.wav')
		self._file = None
		self._listening = False


	@property
	def isListening(self) -> bool:
		return self._listening


	def onStartListening(self, session: DialogSession):
		self._listening = True
		self._file = wave.open(str(self._filepath), 'wb')
		self.MqttManager.mqttClient.subscribe(constants.TOPIC_AUDIO_FRAME.format(session.siteId))


	def onCaptured(self, session: DialogSession):
		self.stopRecording(session.siteId)


	def onSessionError(self, session: DialogSession):
		self.stopRecording(session.siteId)
		self.clean()


	def stopRecording(self, siteId: str):
		self._listening = False
		self.MqttManager.mqttClient.unsubscribe(constants.TOPIC_AUDIO_FRAME.format(siteId))
		self._file.close()


	def onAudioFrame(self, message: mqtt.MQTTMessage):
		try:
			riff, size, fformat = struct.unpack('<4sI4s', message.payload[:12])

			if riff != b'RIFF':
				self.logError('Frame parse error')
				return

			if fformat != b'WAVE':
				self.logError('Frame wrong format')
				return

			chunkHeader = message.payload[12:20]
			subChunkId, subChunkSize = struct.unpack('<4sI', chunkHeader)

			samplerate = 22050
			channels = 2
			if subChunkId == b'fmt ':
				aFormat, channels, samplerate, byterate, blockAlign, bps = struct.unpack('HHIIHH', message.payload[20:36])

			# noinspection PyProtectedMember
			if not self._file._datawritten:
				self._file.setframerate(samplerate)
				self._file.setnchannels(channels)
				self._file.setsampwidth(2)

			chunkOffset = 52
			while chunkOffset < size:
				subChunk2Id, subChunk2Size = struct.unpack('<4sI', message.payload[chunkOffset:chunkOffset + 8])
				chunkOffset += 8
				if subChunk2Id == b'data':
					self._file.writeframes(message.payload[chunkOffset:chunkOffset + subChunk2Size])

				chunkOffset = chunkOffset + subChunk2Size + 8

		except Exception as e:
			self.logError(f'Error capturing user speech: {e}')


	def getSamplePath(self) -> Path:
		return self._filepath


	def getSample(self) -> wave.Wave_write:
		return self._file


	def clean(self):
		self._filepath.unlink()
