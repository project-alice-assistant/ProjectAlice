import json
from pathlib import Path

from core.base.model.Manager import Manager


class NluManager(Manager):

	def __init__(self):
		super().__init__()
		self._nluEngine = None
		self._pathToCache = Path(self.Commons.rootDir(), 'var/cache/nlu')


	def onStart(self):
		self.selectNluEngine()
		if not self.checkCache():
			self.buildCache()

	def onStop(self):
		if self._nluEngine:
			self._nluEngine.stop()


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


	def checkCache(self) -> bool:
		if not self._pathToCache.exists():
			return False

		# Todo check for modifications
		return True


	def buildCache(self):
		self.logInfo('- Building NLU cache')

		cached = dict()

		for skillName, skillInstance in self.SkillManager.allSkills.items():
			pathToResources = skillInstance.getResource(resourcePathFile='dialogTemplate')

			cached[skillName] = dict()
			for file in pathToResources.glob('*.json'):
				cached[skillName][file.stem] = self.Commons.fileChecksum(file)

		with Path(self._pathToCache, 'checksums.json').open('w') as fp:
			fp.write(json.dumps(cached, ident=4))
