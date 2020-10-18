import difflib
from typing import Optional

import requests

from core.ProjectAliceExceptions import GithubNotFound
from core.base.model.Manager import Manager
from core.base.model.Version import Version
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import Online


class SkillStoreManager(Manager):

	SUGGESTIONS_DIFF_LIMIT = 0.75

	def __init__(self):
		super().__init__()
		self._skillStoreData = dict()
		self._skillSamplesData = dict()


	@property
	def skillStoreData(self) -> dict:
		return self._skillStoreData


	def onStart(self):
		self.refreshStoreData()


	def onQuarterHour(self):
		self.refreshStoreData()


	@Online(catchOnly=True)
	def refreshStoreData(self):
		updateChannel = self.ConfigManager.getAliceConfigByName('skillsUpdateChannel')
		req = requests.get(url=f'https://skills.projectalice.io/assets/store/{updateChannel}.json')
		if req.status_code not in {200, 304}:
			return

		self._skillStoreData = req.json()

		if not self.ConfigManager.getAliceConfigByName('suggestSkillsToInstall'):
			return

		req = requests.get(url=f'https://skills.projectalice.io/assets/store/{updateChannel}.samples')
		if req.status_code not in {200, 304}:
			return

		self.prepareSamplesData(req.json())

		strings = [
			'time',
			'give me the date',
			'what time is it',
			'give me money',
			'give me time',
			'shopping list',
			'add something to my shopping list',
			'tell me time',
			'what is blue'
		]

		for string in strings:
			sug = self.findSkillSuggestion(session=None, string=string)
			self.logDebug(f'Found {len(sug)} potential skill for **{string}**: {sug}', plural='skill')


	def prepareSamplesData(self, data: dict):
		if not data:
			return

		junks = self.LanguageManager.getStrings(key='politness', skill='system')
		for skillName, skill in data.items():
			for intent, samples in skill.get(self.LanguageManager.activeLanguage, dict()).items():
				for sample in samples:
					self._skillSamplesData.setdefault(skillName, list())

					for junk in junks:
						if junk in sample:
							sample = sample.replace(junk, '')

					self._skillSamplesData[skillName].append(sample)


	def _getSkillUpdateVersion(self, skillName: str) -> Optional[tuple]:
		versionMapping = self._skillStoreData.get(skillName, dict()).get('versionMapping', dict())

		if not versionMapping:
			raise GithubNotFound

		userUpdatePref = self.ConfigManager.getAliceConfigByName('skillsUpdateChannel')
		skillUpdateVersion = (Version(), '')

		aliceVersion = Version.fromString(constants.VERSION)
		for aliceMinVersion, repoVersion in versionMapping.items():
			aliceMinVersion = Version.fromString(aliceMinVersion)
			repoVersion = Version.fromString(repoVersion)

			if not repoVersion.isVersionNumber or not aliceMinVersion.isVersionNumber or aliceMinVersion > aliceVersion:
				continue

			releaseType = repoVersion.releaseType
			if userUpdatePref == 'master' and releaseType in {'rc', 'b', 'a'} \
					or userUpdatePref == 'rc' and releaseType in {'b', 'a'} \
					or userUpdatePref == 'beta' and releaseType == 'a':
				continue

			if repoVersion > skillUpdateVersion[0]:
				skillUpdateVersion = (repoVersion, f'{str(repoVersion)}_{str(aliceMinVersion)}')

		if not skillUpdateVersion[0].isVersionNumber:
			raise GithubNotFound

		return skillUpdateVersion


	def findSkillSuggestion(self, session: DialogSession, string: str = None) -> set:
		suggestions = set()
		if not self._skillSamplesData or not self.InternetManager.online:
			return suggestions

		userInput = session.previousInput if not string else string
		for skillName, samples in self._skillSamplesData.items():
			for sample in samples:
				diff = difflib.SequenceMatcher(None, userInput, sample).ratio()
				if diff >= self.SUGGESTIONS_DIFF_LIMIT:
					suggestions.add(skillName)
					break

		return suggestions


	def getSkillUpdateTag(self, skillName: str) -> str:
		try:
			return self._getSkillUpdateVersion(skillName)[1]
		except GithubNotFound:
			raise


	def getSkillUpdateVersion(self, skillName: str) -> Version:
		try:
			return self._getSkillUpdateVersion(skillName)[0]
		except GithubNotFound:
			raise


	def getSkillData(self, skillName: str) -> dict:
		return self._skillStoreData.get(skillName, dict())


	def skillExists(self, skillName: str) -> bool:
		return skillName in self._skillStoreData
