from typing import Optional

import requests

from core.ProjectAliceExceptions import GithubNotFound
from core.base.model.Manager import Manager
from core.base.model.Version import Version
from core.commons import constants
from core.util.Decorators import Online


class SkillStoreManager(Manager):
	STORE_URLS = {
		'master': 'http://skills.projectalice.io/assets/store/master.json',
		'rc'    : 'http://skills.projectalice.io/assets/store/rc.json',
		'beta'  : 'http://skills.projectalice.io/assets/store/beta.json',
		'alpha' : 'http://skills.projectalice.io/assets/store/alpha.json'
	}


	def __init__(self):
		super().__init__()
		self._data = dict()


	def onStart(self):
		self.refreshStoreData()


	@Online(catchOnly=True)
	def onQuarterHour(self):
		self.refreshStoreData()


	def refreshStoreData(self):
		updateChannel = self.ConfigManager.getAliceConfigByName('skillsUpdateChannel')
		url = self.STORE_URLS[updateChannel]
		req = requests.get(url)
		if req.status_code not in {200, 304}:
			return

		self._data = req.json()


	def _getSkillUpdateVersion(self, skillName: str) -> Optional[tuple]:
		versionMapping = self._data.get(skillName, dict()).get('versionMapping', dict)

		userUpdatePref = self.ConfigManager.getAliceConfigByName('skillsUpdateChannel')
		skillUpdateVersion = (Version(0, 0, 0, '', 0), 'master')

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
				skillUpdateVersion = (repoVersion, f'{str(repoVersion)}>={str(aliceMinVersion)}')

		if not skillUpdateVersion[0].isVersionNumber:
			raise GithubNotFound

		return skillUpdateVersion


	def getSkillUpdateTag(self, skillName: str) -> str:
		return self._getSkillUpdateVersion(skillName)[1]


	def getSkillUpdateVersion(self, skillName: str) -> Version:
		return self._getSkillUpdateVersion(skillName)[0]


	def getSkillData(self, skillName: str, releaseType: str) -> dict:
		return self._data.get(skillName, dict())
