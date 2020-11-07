import difflib
from random import shuffle
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
		req = requests.get(url=constants.SKILLS_STORE_ASSETS)
		if req.status_code not in {200, 304}:
			return

		self._skillStoreData = req.json()

		if not self.ConfigManager.getAliceConfigByName('suggestSkillsToInstall'):
			return

		req = requests.get(url=constants.SKILLS_SAMPLES_STORE_ASSETS)
		if req.status_code not in {200, 304}:
			return

		self.prepareSamplesData(req.json())


	def prepareSamplesData(self, data: dict):
		if not data:
			return

		for skillName, skill in data.items():
			self._skillSamplesData.setdefault(skillName, skill.get(self.LanguageManager.activeLanguage, list()))


	def _getSkillUpdateVersion(self, skillName: str) -> Optional[tuple]:
		"""
		Get the highest skill version number a user can install.
		This is based on the user preferences, dependending on the current Alice version
		and the user's selected update channel for skills
		In case nothing is found, DO NOT FALLBACK TO MASTER

		:param skillName: The skill to look for
		:return: tuple
		"""
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

		userInput = session.input if not string else string
		if not userInput:
			return suggestions

		for skillName, samples in self._skillSamplesData.items():
			for sample in samples:
				diff = difflib.SequenceMatcher(None, userInput, sample).ratio()
				if diff >= self.SUGGESTIONS_DIFF_LIMIT:
					suggestions.add(skillName)
					break

		userInputs = list()
		userInput = userInput.split()

		if len(userInput) == 1:
			userInputs.append(userInput.copy())

		for _ in range(max(len(userInput), 8)):
			shuffle(userInput)
			userInputs.append(userInput.copy())

		for skillName, samples in self._skillSamplesData.items():
			for sample in samples:
				for userInput in userInputs:
					diff = difflib.SequenceMatcher(None, userInput, sample).ratio()
					if diff >= self.SUGGESTIONS_DIFF_LIMIT:
						suggestions.add(skillName)
						break

		ret = set()
		for suggestedSkillName in suggestions:
			speakableName = self._skillStoreData.get(suggestedSkillName, dict()).get('speakableName', '')

			if not speakableName:
				continue

			ret.add((suggestedSkillName, speakableName))

		return ret


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
