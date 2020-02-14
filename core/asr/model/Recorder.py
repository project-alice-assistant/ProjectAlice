import uuid
from pathlib import Path

import paho.mqtt.client as mqtt
import struct
from pydub import AudioSegment

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession


class Recorder(ProjectAliceObject):

	def __init__(self, session: DialogSession = None):
		super().__init__()
		self._session = session
		self._filepath = Path(f'/tmp/done-{uuid.uuid4()}.wav')
		self._audio: AudioSegment = AudioSegment.empty()
		self._listening = False
		self._minDB = None
		self._maxDB = None
		self._speechDetected = False
		self._recorded = False
		self._silenceCount = 0
		self._buffer = bytearray()


	@property
	def isListening(self) -> bool:
		return self._listening


	def onStartListening(self, session: DialogSession):
		self._listening = True


	# self._audio = wave.open(str(self._filepath), 'wb')
	# self.MqttManager.mqttClient.subscribe(constants.TOPIC_AUDIO_FRAME.format(session.siteId))


	def captured(self):
		self.stopRecording(self._session.siteId)
		self.ASRManager.onRecorded(self._session)


	def onSessionError(self, session: DialogSession):
		self.stopRecording(session.siteId)
		self.clean()


	def stopRecording(self, siteId: str):
		self._listening = False


	# self.MqttManager.mqttClient.unsubscribe(constants.TOPIC_AUDIO_FRAME.format(siteId))
	# self._audio.export(str(self._filepath), format='wav')


	def decodeStream(self):
		i = 0
		self
		while True:
			buf = self._buffer[i:512]
			if not buf:
				continue

			i += 512


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

			chunkOffset = 52
			while chunkOffset < size:
				subChunk2Id, subChunk2Size = struct.unpack('<4sI', message.payload[chunkOffset:chunkOffset + 8])
				chunkOffset += 8
				if subChunk2Id == b'data':
					self._buffer.append(message.payload[chunkOffset:chunkOffset + subChunk2Size])
				# sound = AudioSegment(
				# 	data=message.payload[chunkOffset:chunkOffset + subChunk2Size],
				# 	sample_width=4,
				# 	frame_rate=samplerate,
				# 	channels=channels
				# )
				# self._audio += sound
				#
				# if self._minDB is None:
				# 	self._minDB = sound.dBFS
				# 	self._maxDB = sound.dBFS
				# else:
				# 	if sound.dBFS > self._maxDB:
				# 		self._maxDB = sound.dBFS
				#
				# 	if self._maxDB > self._minDB + 15:
				# 		self._speechDetected = True
				#
				# 	if self._speechDetected and sound.dBFS <= self._minDB + 2:
				# 		self._silenceCount += 1
				# 		if self._silenceCount > 50:
				# 			self._recorded = True

				chunkOffset = chunkOffset + subChunk2Size + 8

		# if self._recorded:
		# 	self.captured()

		except Exception as e:
			self.logError(f'Error capturing user speech: {e}')


	def getSamplePath(self) -> Path:
		return self._filepath


	def clean(self):
		self._filepath.unlink()
