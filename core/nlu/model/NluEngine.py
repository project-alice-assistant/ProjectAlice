#  Copyright (c) 2021
#
#  This file, NluEngine.py, is part of Project Alice.
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
import importlib
import subprocess
import time
from pathlib import Path

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.webui.model.UINotificationType import UINotificationType


class NluEngine(ProjectAliceObject):
	NAME = ''


	def __init__(self):
		super().__init__()
		self._timer = None
		self._trainingStartTime = 0


	def start(self):
		self.logInfo(f'Starting {self.NAME}')


	def stop(self):
		self.logInfo(f'Stopping {self.NAME}')


	def checkLanguage(self):
		if importlib.util.find_spec(f"snips_nlu_{self.LanguageManager.activeLanguage}") is None:
			subprocess.run(['./venv/bin/snips-nlu', 'download', self.LanguageManager.activeLanguage])


	def train(self, forceLocalTraining: bool = False) -> bool:
		if self.NluManager.training:
			self.logWarning("NLU is already training, can't train again now")
			return False

		self.checkLanguage()
		self.logInfo(f'Training {self.NAME}')
		self._trainingStartTime = time.time()
		self.startTraining()

		return True


	def convertDialogTemplate(self, file: Path):
		self.logFatal(f'NLU Engine {self.NAME} is missing implementation of "convertDialogTemplate"')


	def trainingFailed(self, reason: str = ''):
		self.logError(f'{self.NAME} training failed: {reason}', printStack=False)
		self._timer.cancel()
		self.NluManager.training = False
		self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'failed'})

		self.WebUINotificationManager.newNotification(
			typ=UINotificationType.ERROR,
			notification='nluTrainingFailed',
			key='nluTraining'
		)


	def startTraining(self):
		self.NluManager.training = True
		self._timer = self.ThreadManager.newTimer(interval=0.25, func=self.trainingStatus)


	def trainingFinished(self, trainedData: Path):
		timer = round(time.time() - self._trainingStartTime, 2)

		self.logInfo(f'NLU trained in {timer} seconds')
		self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'done'})
		self.WebUINotificationManager.newNotification(
			typ=UINotificationType.INFO,
			notification='nluTrainingDone',
			key='nluTraining'
		)

		self.ThreadManager.getEvent('TrainAssistant').clear()

		if self._timer:
			self._timer.cancel()

		self.broadcast(method=constants.EVENT_NLU_TRAINED, exceptions=[constants.DUMMY], propagateToSkills=True)
		self.NluManager.training = False
		self.NluManager.restartEngine()


	def trainingStatus(self, dots: str = ''):
		count = dots.count('.')
		if not dots or count > 7:
			dots = '.'
		else:
			dots += '.'

		self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'training'})

		self.WebUINotificationManager.newNotification(
			typ=UINotificationType.INFO,
			notification='nluTraining',
			key='nluTraining',
			replaceBody=[dots]
		)

		self._timer = self.ThreadManager.newTimer(interval=1, func=self.trainingStatus, args=[dots])


	def getLanguage(self) -> str:
		"""
		Get the language that should be used for the training.
		Currently, only portuguese needs a special handling
		:return:
		"""
		lang = self.LanguageManager.activeLanguage
		if lang == 'pt':
			lang = lang + '_' + self.LanguageManager.activeCountryCode.lower()
		return lang
