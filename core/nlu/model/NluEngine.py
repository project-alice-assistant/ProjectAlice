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

from pathlib import Path

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.webui.model.UINotificationType import UINotificationType


class NluEngine(ProjectAliceObject):
	NAME = ''


	def __init__(self):
		super().__init__()


	def start(self):
		self.logInfo(f'Starting {self.NAME}')


	def stop(self):
		self.logInfo(f'Stopping {self.NAME}')


	def train(self):
		self.logInfo(f'Training {self.NAME}')


	def convertDialogTemplate(self, file: Path):
		self.logFatal(f'NLU Engine {self.NAME} is missing implementation of "convertDialogTemplate"')


	def trainingFailed(self, reason: str = ''):
		self.logError(f'{self.NAME} training failed: {reason}', printStack=False)
		self.NluManager.training = False
		self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'failed'})

		self.WebUINotificationManager.newNotification(
			typ=UINotificationType.ERROR,
			notification='nluTrainingFailed',
			key='nluTraining'
		)


	def trainingFinished(self, trainedData: Path, timer: float):
		self.logFatal(f'NLU Engine {self.NAME} is missing implementation of "trainingFinished"')


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
