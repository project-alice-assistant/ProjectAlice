import queue
import wave

import struct
import webrtcvad
from paho.mqtt.client import MQTTMessage

from core.base.model.Manager import Manager
from core.commons import constants


class VadManager(Manager):

	def __init__(self):
		super().__init__()
		self._buffer = queue.Queue()
		self._vad = webrtcvad.Vad(3)
		self._buff = b''
		self._wf = wave.open('/home/pi/ProjectAlice/test.wav', 'wb')
		self._wf.setnchannels(1)
		self._wf.setframerate(16000)
		self._wf.setsampwidth(2)


	def onBooted(self):
		return


	def onStop(self):
		self.MqttManager.mqttClient.unsubscribe(constants.TOPIC_AUDIO_FRAME.format('office'))
		self._buff = b''
		self._wf.close()


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
				#frame = self.resample(message.payload[chunkOffset:chunkOffset + subChunk2Size])
				#self._buffer.put(frame)
				self._buff += message.payload[chunkOffset:chunkOffset + subChunk2Size]
				self._wf.writeframes(message.payload[chunkOffset:chunkOffset + subChunk2Size])

			chunkOffset = chunkOffset + subChunk2Size + 8


	def frameGenerator(self):
		while len(self._buff) < 640:
			continue

		while True:
			chunk = self._buff[:640]
			self._buff.replace(self._buff[:640], b'')
			yield chunk


	def vadDetector(self):
		while True:
			inSpeech = False
			for frame in self.frameGenerator():
				now = self._vad.is_speech(frame, 16000)

				if inSpeech and not now:
					inSpeech = False
					self.broadcast(
						method='vadDown',
						exceptions=self.name,
						propagateToSkills=True,
						siteId='default'
					)
				elif not inSpeech and now:
					inSpeech = True
					print('speech')
					self.broadcast(
						method='vadUp',
						exceptions=self.name,
						propagateToSkills=True,
						siteId='default'
					)
