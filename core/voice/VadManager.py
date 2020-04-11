from queue import Queue

import struct
import webrtcvad
from paho.mqtt.client import MQTTMessage

from core.base.model.Manager import Manager


class VadManager(Manager):

	def __init__(self):
		super().__init__()
		self._buffer = Queue()
		self._vad = webrtcvad.Vad(3)


	def onBooted(self):
		#self.MqttManager.mqttClient.subscribe(constants.TOPIC_AUDIO_FRAME.format('office'))
		self.ThreadManager.newThread(name='vadDetector', target=self.vadDetector)


	def onAudioFrame(self, message: MQTTMessage, siteId: str):
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


	def frameGenerator(self):
		while True:
			yield self._buffer.get()


	def vadDetector(self):
		for frame in self.frameGenerator():
			if len(frame) < 640:
				return

			print(self._vad.is_speech(frame, 16000))
