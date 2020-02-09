import typing

import paho.mqtt.client as mqtt
import struct

from core.asr.model.ASR import ASR
from core.commons import constants


class PocketSphinxASR(ASR):

	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._listening = False
		self._streams: typing.Dict[str: bytearray] = dict()


	def onStart(self):
		pass


	def onAudioFrame(self, message: mqtt.MQTTMessage):
		try:
			riff, size, fformat = struct.unpack('<4sI4s', message.payload[:12])

			if riff != b'RIFF':
				self.logError('Frame capture error')
				return

			if fformat != b'WAVE':
				self.logError('Frame format error')
				return

			chunkOffset = 52
			while chunkOffset < size:
				subChunk2Id, subChunk2Size = struct.unpack('<4sI', message.payload[chunkOffset:chunkOffset + 8])
				chunkOffset += 8
				if subChunk2Id == b'data':
					self._streams[self.Commons.parseSiteId(message)] += message.payload[chunkOffset:chunkOffset + subChunk2Size]

				chunkOffset = chunkOffset + subChunk2Size + 8

		except Exception as e:
			self.logError(f'Error capturing audio frame: {e}')


	def onListen(self, siteId: str):
		self._listening = True
		self._streams[siteId] = bytearray(2048)
		self.MqttManager.mqttClient.unsubscribe(constants.TOPIC_AUDIO_FRAME.format(siteId))


	@property
	def isListening(self) -> bool:
		return self._listening
