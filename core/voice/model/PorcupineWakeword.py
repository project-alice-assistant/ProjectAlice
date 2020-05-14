import queue
import sys
import time
import wave

import io
import os
import pvporcupine
from paho.mqtt.client import MQTTMessage

from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.voice.model.WakewordEngine import WakewordEngine

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../venv/lib/python3.7/site-packages/pvporcupine/binding/python'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../venv/lib/python3.7/site-packages/pvporcupine/resources/util/python'))

# noinspection PyUnresolvedReferences
from porcupine import Porcupine #NOSONAR
# noinspection PyUnresolvedReferences
from util import * #NOSONAR

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
		self._handler = pvporcupine.create(keywords=['porcupine', 'bumblebee'])


	def onBooted(self):
		super().onBooted()
		self._working.set()
		self._hotwordThread = self.ThreadManager.newThread(name='HotwordThread', target=self.worker)


	def onStop(self):
		self._working.clear()


	def onHotwordToggleOff(self, siteId: str, session):
		self._working.clear()
		self._buffer = queue.Queue()


	def onHotwordToggleOn(self, siteId: str, session: DialogSession):
		self._working.set()


	def onAudioFrame(self, message: MQTTMessage, siteId: str):
		if not self._working.is_set():
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
			if not self._working.is_set():
				print('sleep')
				time.sleep(0.1)
				continue

			result = self._handler.process(self._buffer.get())
			if result and result > 0:
				self.logDebug('Detected wakeword')
				self.MqttManager.publish(
					topic=constants.TOPIC_HOTWORD_DETECTED,
					payload={
						'siteId': 'office'
					}
				)
