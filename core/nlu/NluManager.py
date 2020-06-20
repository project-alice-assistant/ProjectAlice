from pathlib import Path

import shutil

from core.base.model.Manager import Manager


class NluManager(Manager):

	def __init__(self):
		super().__init__()
		self._nluEngine = None
		self._pathToCache = Path(self.Commons.rootDir(), 'var/cache/nlu/trainingData')
		if not self._pathToCache.exists():
			self._pathToCache.mkdir(parents=True)

		self.selectNluEngine()


	def onStop(self):
		super().onStop()

		if self._nluEngine:
			self._nluEngine.stop()


	def checkData(self) -> bool:
		return self.checkEngine() and self.checkCachedData()


	def checkCachedData(self) -> bool:
		skills = self.SkillManager.allSkills

		for file in self._pathToCache.glob('*.json'):
			if file.stem.split('_')[0] not in skills:
				return False

		return True


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
			return

		self._nluEngine.start()


	def buildTrainingData(self):
		from core.dialog.DialogTemplateManager import DialogTemplateManager
		self.clearCache()
		for path in DialogTemplateManager.skillResource():
			self._nluEngine.convertDialogTemplate(path)


	def train(self):
		self.buildTrainingData()
		self.trainNLU()


	def trainNLU(self):
		self._nluEngine.train()


	def clearCache(self):
		shutil.rmtree(self._pathToCache)
		self._pathToCache.mkdir()
