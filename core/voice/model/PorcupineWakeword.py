import os
import sys

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
		self._hotwordThread = None


	def onStart(self):
		super().onStart()
		self._hotwordThread = self.ThreadManager.newThread(name='HotwordThread', target=self.worker)


	def onStop(self):
		self._working.clear()


	def onHotwordToggleOff(self, siteId: str, session):
		self._working.clear()


	def onHotwordToggleOn(self, siteId: str, session: DialogSession):
		self._hotwordThread = self.ThreadManager.newThread(name='HotwordThread', target=self.worker)


	def worker(self):
		self._working.set()
		porcupine = Porcupine(
			library_path=LIBRARY_PATH,
			model_file_path=MODEL_FILE_PATH,
			keyword_file_paths=[KEYWORD_FILE_PATHS['bumblebee']],
			sensitivities=[0.5]
		)
		while self._working.is_set():
			result = porcupine.process()
			if result:
				self.logDebug('Detected wakeword')
				self.MqttManager.publish(
					topic=constants.TOPIC_HOTWORD_DETECTED
				)
