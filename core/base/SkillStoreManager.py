#  Copyright (c) 2021
#
#  This file, SkillStoreManager.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:46 CEST

import difflib
from random import shuffle
from typing import Optional, Tuple

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
		super().onStart()
		self.refreshStoreData()


	def onBooted(self):
		super().onBooted()
		self.refreshStoreData()


	def onQuarterHour(self):
		self.refreshStoreData()


	@Online(catchOnly=True)
	def refreshStoreData(self):
		req = requests.get(url=constants.SKILLS_STORE_ASSETS)
		if req.status_code not in {200, 304}:
			return

		self._skillStoreData = req.json()
		self.checkConditions()

		if not self.ConfigManager.getAliceConfigByName('suggestSkillsToInstall'):
			return

		req = requests.get(url=constants.SKILLS_SAMPLES_STORE_ASSETS)
		if req.status_code not in {200, 304}:
			return

		self.prepareSamplesData(req.json())


	def checkConditions(self):
		for skillName, skillData in self._skillStoreData.items():
			skillData['installed'] = skillName in self.SkillManager.allSkills.keys()

			offendingConditions = self.SkillManager.checkSkillConditions(installer=skillData, checkOnly=True)
			skillData['offendingConditions'] = offendingConditions
			skillData['compatible'] = False if len(offendingConditions) > 0 else True


	def prepareSamplesData(self, data: dict):
		if not data:
			return

		for skillName, skill in data.items():
			self._skillSamplesData.setdefault(skillName, skill.get(self.LanguageManager.activeLanguage, list()))


	def _getSkillUpdateVersion(self, skillName: str) -> Optional[Tuple[Version, str]]:
		"""
		Get the highest skill version number a user can install.
		This is based on the user preferences, depending on the current Alice version
		and the user's selected update channel for skills
		In case nothing is found, DO NOT FALLBACK TO MASTER

		:param skillName: The skill to look for
		:return: tuple (Version object, tag string)
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
				sample = sample.split()
				for userInput in userInputs:
					diff = difflib.SequenceMatcher(None, userInput, sample).ratio()
					if diff >= self.SUGGESTIONS_DIFF_LIMIT:
						suggestions.add(skillName)
						break

		ret = set()
		for suggestedSkillName in suggestions:
			speakableName = self._skillStoreData.get(suggestedSkillName, dict()).get('speakableName', '')

			if not speakableName:
				self.logDebug(f'No speakable name for skill suggestion **{suggestedSkillName}** in install file. Please add or ask the author to do so.')
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


	def getStoreData(self) -> dict:
		return self._skillStoreData
