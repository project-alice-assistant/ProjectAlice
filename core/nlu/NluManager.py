import json
from pathlib import Path
from typing import Dict

from core.base.model.Manager import Manager


class NluManager(Manager):

	def __init__(self):
		super().__init__()
		self._nluEngine = None
		self._pathToChecksums = Path(self.Commons.rootDir(), 'var/cache/nlu/checksums.json')


	def onStart(self):
		self.selectNluEngine()
		if not self._pathToChecksums.exists():
			self.buildCache()
			self.trainNLU()

		changes = self.checkCache()
		if not changes:
			self.logInfo('Cache uptodate')
		else:
			self.trainNLU(changes)


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


	def checkCache(self) -> Dict[str, list]:
		with self._pathToChecksums.open() as fp:
			checksums = json.load(fp)

		changes = dict()

		for skillName, skillInstance in self.SkillManager.allSkills.items():
			self.logInfo(f'Checking data for skill "{skillName}"')
			if skillName not in checksums:
				self.logInfo(f'Skill "{skillName}" is new')
				changes[skillName] = list()
				continue

			pathToResources = skillInstance.getResource(resourcePathFile='dialogTemplate')
			for file in pathToResources.glob('*.json'):
				filename = file.stem
				if filename not in checksums[skillName]:
					self.logInfo(f'Skill "{skillName}" has new language support "{filename}"')
					changes.setdefault(skillName, list()).append(filename)
					continue

				if self.Commons.fileChecksum(file) != checksums[skillName][filename]:
					self.logInfo(f'Skill "{skillName}" has changes in language "{filename}"')
					changes.setdefault(skillName, list()).append(filename)
					continue

		return changes


	def buildCache(self):
		self.logInfo('- Building NLU cache')

		cached = dict()

		for skillName, skillInstance in self.SkillManager.allSkills.items():
			pathToResources = skillInstance.getResource(resourcePathFile='dialogTemplate')

			cached[skillName] = dict()
			for file in pathToResources.glob('*.json'):
				cached[skillName][file.stem] = self.Commons.fileChecksum(file)

		with self._pathToChecksums.open('w') as fp:
			fp.write(json.dumps(cached, indent=4, sort_keys=True))


	def trainNLU(self, changes: dict = None):
		pass
