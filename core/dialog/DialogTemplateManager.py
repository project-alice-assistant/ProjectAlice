import json
from pathlib import Path
from typing import Dict, Generator

from core.base.model.Manager import Manager
from core.dialog.model.DialogTemplate import DialogTemplate


class DialogTemplateManager(Manager):

	def __init__(self):
		super().__init__()

		self._pathToCache = Path(self.Commons.rootDir(), 'var/cache/dialogTemplates/')
		self._pathToCache.mkdir(parents=True, exist_ok=True)

		self._pathToChecksums = self._pathToCache / 'checksums.json'
		self._pathToData = self._pathToCache / 'data.json'

		self._hasChanges = False
		self._updatedData: Dict[str, list] = dict()

		if not self._pathToChecksums.exists():
			self._pathToChecksums.write_text('{}')

		if not self._pathToData.exists():
			self._pathToData.write_text('{}')

		self._dialogTemplates = dict()
		self._slotTypes = dict()


	@property
	def hasChanges(self) -> bool:
		return self._hasChanges


	@property
	def updatedData(self) -> Dict[str, list]:
		return self._updatedData


	def onStart(self):
		super().onStart()
		self._loadData()

		changes = self.checkCache()
		if not changes:
			self.logInfo('Cache uptodate')
		else:
			self.buildCache()


	def _loadData(self):
		for resource in self.skillResource():
			data = json.loads(resource.read_text())
			dialogTemplate = DialogTemplate(**data)
			self._dialogTemplates[dialogTemplate.skill] = dialogTemplate

			for slot in dialogTemplate.allSlots:
				if slot.name in self._slotTypes:
					self.logInfo(f'Skill **{dialogTemplate.skill}** extends slot **{slot.name}**')

				self._slotTypes[slot.name] = [*self._slotTypes.get(slot.name, list()), *slot.values]

		data = list()
		for skillName, skillData in self._dialogTemplates.items():
			data.append(skillData)

		#self._pathToData.write_text(data=json.dumps(data, ensure_ascii=True, indent=4))



	def afterSkillChange(self):
		if self.checkCache():
			self.buildCache()


	def checkCache(self) -> Dict[str, list]:
		self._hasChanges = False

		with self._pathToChecksums.open() as fp:
			checksums = json.load(fp)

		# First check upon the skills that are installed and active
		changes = dict()
		language = self.LanguageManager.activeLanguage
		for skillName, skillInstance in self.SkillManager.allWorkingSkills.items():

			self.logInfo(f'Checking data for skill **{skillName}**')
			if skillName not in checksums:
				self.logInfo(f'Skill **{skillName}** is new')
				checksums[skillName] = list()
				changes[skillName] = list()

			pathToResources = skillInstance.getResource('dialogTemplate')
			if not pathToResources.exists():
				self.logWarning(f'**{skillName}** has no dialog template defined')
				changes.pop(skillName, None)
				continue

			for file in pathToResources.glob('*.json'):
				filename = file.stem
				if filename not in checksums[skillName]:
					# Trigger a change only if the change concerns the language in use
					if filename == language:
						self.logInfo(f'Skill **{skillName}** has new language support **{filename}**')
						changes.setdefault(skillName, list()).append(filename)
					continue

				if self.Commons.fileChecksum(file) != checksums[skillName][filename] and filename == language:
					# Trigger a change only if the change concerns the language in use
					self.logInfo(f'Skill **{skillName}** has changes in language **{filename}**')
					changes.setdefault(skillName, list()).append(filename)

		# Now check that what we have in cache in actually existing and wasn't manually deleted
		for skillName, languages in checksums.items():
			if not Path(self.Commons.rootDir(), f'skills/{skillName}/').exists():
				self.logInfo(f'Skill **{skillName}** was removed')
				changes[f'--{skillName}'] = list()
				continue

			for lang in languages:
				if not Path(self.Commons.rootDir(), f'skills/{skillName}/dialogTemplate/{lang}.json').exists() and lang == language:
					self.logInfo(f'Skill **{skillName}** has dropped language **{lang}**')
					changes.setdefault(f'--{skillName}', list()).append(lang)

		if changes:
			self._hasChanges = True
			self._updatedData = changes

		return changes


	def buildCache(self):
		self.logInfo('Building dialog templates cache')

		cached = dict()

		for skillName, skillInstance in self.SkillManager.allWorkingSkills.items():
			pathToResources = skillInstance.getResource('dialogTemplate')
			if not pathToResources.exists():
				self.logWarning(f'**{skillName}** has no dialog template defined to build cache')
				continue

			cached[skillName] = dict()
			for file in pathToResources.glob('*.json'):
				cached[skillName][file.stem] = self.Commons.fileChecksum(file)

		self._pathToChecksums.write_text(json.dumps(cached, indent=4, sort_keys=True))


	def cleanCache(self, skillName: str):
		for file in Path(self._pathToCache, 'trainingData').glob('*.json'):
			if file.stem.startswith(f'{skillName}_'):
				file.unlink()

		checksums = json.load(self._pathToChecksums)
		checksums.pop(skillName, None)

		self._pathToChecksums.write_text(json.dumps(checksums, indent=4, sort_keys=True))


	def clearCache(self, rebuild: bool = True):
		if self._pathToChecksums.exists():
			self._pathToChecksums.write_text(json.dumps(dict()))
			self.logInfo('Cache cleared')

		if rebuild:
			self.checkCache()
			self.buildCache()


	def skillResource(self) -> Generator[Path, None, None]:
		for skillName, skillInstance in self.SkillManager.allWorkingSkills.items():
			resource = skillInstance.getResource(f'dialogTemplate/{self.LanguageManager.activeLanguage}.json')
			if not resource.exists():
				continue

			yield resource
