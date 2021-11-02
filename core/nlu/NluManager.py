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

import shutil
from pathlib import Path

from core.base.model.Manager import Manager
from core.base.model.StateType import StateType


class NluManager(Manager):

	def __init__(self):
		super().__init__()
		self._nluEngine = None
		self._pathToCache = Path(self.Commons.rootDir(), 'var/cache/nlu/trainingData')
		if not self._pathToCache.exists():
			self._pathToCache.mkdir(parents=True)
		self._training = False


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


	def checkEngine(self) -> bool:
		if not Path(self.Commons.rootDir(), f'assistant/nlu_engine').exists():
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


	def trainNLU(self):
		self._nluEngine.train()


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
