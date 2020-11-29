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
