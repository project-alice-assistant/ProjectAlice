import json
from pathlib import Path
from typing import Dict

from core.base.model.Manager import Manager


class DialogTemplateManager(Manager):

	def __init__(self):
		super().__init__()

		self._pathToCache = Path(self.Commons.rootDir(), 'var/cache/dialogTemplates/')
		self._pathToChecksums = self._pathToCache / 'checksums.json'
		self._hasChanges = False
		self._updatedData: Dict[str, list] = dict()


	@property
	def hasChanges(self) -> bool:
		return self._hasChanges


	@property
	def updatedData(self) -> Dict[str, list]:
		return self._updatedData


	def onStart(self):
		super().onStart()

		changes = self.checkCache()
		if not changes:
			self.logInfo('Cache uptodate')
		else:
			self.buildCache()


	def afterNewSkillInstall(self):
		if self.checkCache():
			self.buildCache()


	def checkCache(self) -> Dict[str, list]:
		self._hasChanges = False

		with self._pathToChecksums.open() as fp:
			checksums = json.load(fp)

		# First check upon the skills that are installed
		changes = dict()
		language = self.LanguageManager.activeLanguage
		for skill in Path(self.Commons.rootDir(), 'skills/').glob('*/'):
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

		if changes:
			self._hasChanges = True
			self._updatedData = changes

		return changes


	def buildCache(self):
		self.logInfo('Building dialog templates cache')

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


	def cleanCache(self, skillName: str):
		for file in Path(self._pathToCache, 'trainingData').glob('*.json'):
			if file.stem.startswith(f'{skillName}_'):
				file.unlink()

		with self._pathToChecksums.open() as fp:
			checksums = json.load(fp)
			checksums.pop(skillName, None)

		with self._pathToChecksums.open('w') as fp:
			fp.write(json.dumps(checksums, indent=4, sort_keys=True))


	def clearCache(self, rebuild: bool = True):
		if self._pathToChecksums.exists():
			with self._pathToChecksums.open('w') as fp:
				fp.write(json.dumps(dict()))
				self.logInfo('Cache cleared')

		if rebuild:
			self.checkCache()
			self.buildCache()


	def skillResource(self) -> Path:
		for skillPath in Path(self.Commons.rootDir(), 'skills/').glob('*/'):
			if skillPath.is_file() or skillPath.stem.startswith('_'):
				continue

			resource = skillPath / f'dialogTemplate/{self.LanguageManager.activeLanguage}.json'
			if not resource.exists():
				continue

			yield resource
