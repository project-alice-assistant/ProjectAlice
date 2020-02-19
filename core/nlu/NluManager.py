import json
from pathlib import Path
from typing import Dict

from core.base.model.Manager import Manager


class NluManager(Manager):

	def __init__(self):
		super().__init__()
		self._nluEngine = None
		self._pathToCache = Path(self.Commons.rootDir(), 'var/cache/nlu/')
		self._pathToChecksums = self._pathToCache / 'checksums.json'
		self.selectNluEngine()


	def onStart(self):
		changes = self.checkCache()
		if not changes:
			self.logInfo('Cache uptodate')
		else:
			self.buildTrainingData(changes)
			self.buildCache()
			self.trainNLU()


	def onStop(self):
		if self._nluEngine:
			self._nluEngine.stop()


	def afterNewSkillInstall(self):
		self.onStart()


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

		# First check upon the skills that are installed
		changes = dict()
		language = self.LanguageManager.activeLanguage
		for skill in Path(self.Commons.rootDir(), 'skills/').glob('*'):
			if skill.is_file() or skill.stem.startswith('_'):
				continue

			skillName = skill.stem
			self.logInfo(f'Checking data for skill "{skillName}"')
			if skillName not in checksums:
				self.logInfo(f'Skill "{skillName}" is new')
				checksums[skillName] = list()
				changes[skillName] = list()

			pathToResources = skill / 'dialogTemplate'
			if not pathToResources.exists():
				self.logWarning(f'{skillName} has no dialog template defined')
				continue

			for file in pathToResources.glob('*.json'):
				filename = file.stem
				if filename not in checksums[skillName]:
					# Trigger a change only if the change concerns the language in use
					if filename == language:
						self.logInfo(f'Skill "{skillName}" has new language support "{filename}"')
						changes.setdefault(skillName, list()).append(filename)
					continue

				if self.Commons.fileChecksum(file) != checksums[skillName][filename]:
					# Trigger a change only if the change concerns the language in use
					if filename == language:
						self.logInfo(f'Skill "{skillName}" has changes in language "{filename}"')
						changes.setdefault(skillName, list()).append(filename)
					continue

		# Now check that what we have in cache in actually existing and wasn't manually deleted
		for skillName, languages in checksums.items():
			if not Path(self.Commons.rootDir(), f'skills/{skillName}/').exists():
				self.logInfo(f'Skill "{skillName}" was removed')
				changes[f'--{skillName}'] = list()
				continue

			for lang in languages:
				if not Path(self.Commons.rootDir(), f'skills/{skillName}/dialogTemplate/{lang}.json').exists() and lang == language:
					self.logInfo(f'Skill "{skillName}" has dropped language "{lang}"')
					changes.setdefault(f'--{skillName}', list()).append(lang)

		return changes


	def buildCache(self):
		self.logInfo('Building NLU cache')

		cached = dict()

		for skill in Path(self.Commons.rootDir(), 'skills/').glob('*'):
			if skill.is_file() or skill.stem.startswith('_'):
				continue

			skillName = skill.stem
			pathToResources = skill / 'dialogTemplate'
			if not pathToResources.exists():
				self.logWarning(f'{skillName} has no dialog template defined to build cache')
				continue

			cached[skillName] = dict()
			for file in pathToResources.glob('*.json'):
				cached[skillName][file.stem] = self.Commons.fileChecksum(file)

		with self._pathToChecksums.open('w') as fp:
			fp.write(json.dumps(cached, indent=4, sort_keys=True))


	def buildTrainingData(self, changes: dict):
		for changedSkill, changedLanguages in changes.items():
			if not changedSkill.startswith('--'):
				pathToSkillResources = Path(self.Commons.rootDir(), f'skills/{changedSkill}/dialogTemplate')

				for lang in changedLanguages:
					self._nluEngine.convertDialogTemplate(pathToSkillResources / f'{lang}.json')
			else:
				skillName = changedSkill.replace('--', '')

				with self._pathToChecksums.open() as fp:
					checksums = json.load(fp)

				if not changedLanguages:
					checksums.pop(skillName, None)
					for file in Path(self.Commons.rootDir(), '/var/cache/nlu/trainingData/').glob(f'{skillName}_'):
						file.unlink()
				else:
					for lang in changedLanguages:
						checksums.get(skillName, list()).pop(lang, None)
						langFile = Path(self.Commons.rootDir(), f'/var/cache/nlu/trainingData/{skillName}_{lang}.json')
						if langFile.exists():
							langFile.unlink()


	def trainNLU(self):
		self._nluEngine.train()


	def cleanCache(self, skillName: str):
		for file in Path(self._pathToCache, 'trainingData').glob('*.json'):
			if file.stem.startswith(f'{skillName}_'):
				file.unlink()

		with self._pathToChecksums.open() as fp:
			checksums = json.load(fp)
			checksums.pop(skillName, None)

		with self._pathToChecksums.open('w') as fp:
			fp.write(json.dumps(checksums, indent=4, sort_keys=True))
