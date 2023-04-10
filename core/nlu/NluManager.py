#  Copyright (c) 2021
#
#  This file, NluManager.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:47 CEST
import hashlib
import shutil
import threading
from paho.mqtt import client as mqtt
from pathlib import Path
from typing import Optional

from core.base.model.Manager import Manager
from core.base.model.StateType import StateType
from core.commons import constants
from core.nlu.model.NluEngine import NluEngine


class NluManager(Manager):

	def __init__(self):
		super().__init__()
		self._nluEngine = None
		self._pathToCache = Path(self.Commons.rootDir(), 'var/cache/nlu/trainingData')
		if not self._pathToCache.exists():
			self._pathToCache.mkdir(parents=True)
		self._training = False
		self._offshoreTrainerReady = False
		self._offshoreRespondTimer: threading.Timer = Optional[None]


	def onStart(self):
		super().onStart()
		self.selectNluEngine()


	def onStop(self):
		super().onStop()

		if self._nluEngine:
			self._nluEngine.stop()


	def restartEngine(self):
		self.selectNluEngine()
		self._nluEngine.start()


	def onBooted(self):
		super().onBooted()
		self._nluEngine.start()


	def offshoreTrainerReady(self):
		self._offshoreTrainerReady = True


	def offshoreTrainerStopped(self):
		self._offshoreTrainerReady = False


	def offshoreTrainerResult(self, msg: mqtt.MQTTMessage):
		try:
			controlHash = Path(msg.topic).stem
			tempTrainingData = Path('/tmp/snipsNLU')

			with open(tempTrainingData.with_suffix('.zip'), 'wb') as fp:
				fp.write(msg.payload)

			self.logInfo('Received trained NLU from offshore trainer')
			fileHash = hashlib.blake2b(tempTrainingData.with_suffix('.zip').read_bytes()).hexdigest()

			if fileHash == controlHash:
				self.logInfo('File control hashes match')
			else:
				self.logWarning('File control hashes do not match')
				self.nluEngine.trainingFailed()
				return

			shutil.unpack_archive(tempTrainingData.with_suffix('.zip'), tempTrainingData, 'zip')
			self.training = False
			self.nluEngine.trainingFinished(trainedData=tempTrainingData)
		except Exception as e:
			self.nluEngine.trainingFailed(str(e))


	def offshoreTrainerRefusedFailed(self, reason: str):
		self._nluEngine.trainingFailed(reason)


	def offshoreTrainerTraining(self):
		if self._offshoreRespondTimer:
			self._offshoreRespondTimer.cancel()
		self.training = True
		self.logInfo('Offshore trainer answered and is training')


	def startOffshoreTraining(self, dataset: dict):
		self.logInfo('Asking offshore NLU trainer')
		self._offshoreRespondTimer = self.ThreadManager.newTimer(interval=5, func=self.offshoreTrainerFailedResponding)

		self.MqttManager.publish(
			topic=constants.TOPIC_NLU_TRAINER_TRAIN,
			payload={
				'data': dataset,
				'language': self._nluEngine.getLanguage()
			}
		)


	def offshoreTrainerFailedResponding(self):
		self.offshoreTrainerRefusedFailed('No response from offshore trainer')
		self.logInfo('Start local training')
		self.trainNLU(forceLocalTraining=True)


	def checkEngine(self) -> bool:
		if not Path(self.Commons.rootDir(), 'assistant/nlu_engine').exists():
			if Path(self.Commons.rootDir(), f'trained/assistants/{self.LanguageManager.activeLanguage}/nlu_engine').exists():
				self.AssistantManager.linkAssistant()
				return True
			else:
				return False
		else:
			return True


	def selectNluEngine(self):
		if self._nluEngine:
			self._nluEngine.stop()

		if self.ConfigManager.getAliceConfigByName('nluEngine') == 'snips':
			from core.nlu.model.SnipsNlu import SnipsNlu

			self._nluEngine = SnipsNlu()
		else:
			self.logFatal(f'Unsupported NLU engine: {self.ConfigManager.getAliceConfigByName("nluEngine")}')
			self.ProjectAlice.onStop()


	def buildTrainingData(self):
		self.clearCache()
		self._nluEngine.convertDialogTemplate(self.DialogTemplateManager.pathToData)


	def train(self):
		self.buildTrainingData()
		self.trainNLU()


	def trainNLU(self, forceLocalTraining: bool = False):
		if not self.ProjectAlice.isBooted:
			forceLocalTraining = True

		self._nluEngine.train(forceLocalTraining=forceLocalTraining)


	def clearCache(self):
		shutil.rmtree(self._pathToCache)
		self._pathToCache.mkdir()


	@property
	def training(self) -> bool:
		return self._training


	@training.setter
	def training(self, value: bool):
		self._training = value

		if not value:
			self.StateManager.setState('projectalice.core.training', newState=StateType.FINISHED)


	@property
	def nluEngine(self) -> NluEngine:
		return self._nluEngine
