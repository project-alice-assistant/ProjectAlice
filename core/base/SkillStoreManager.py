import json
from typing import Optional

import requests

from core.ProjectAliceExceptions import GithubNotFound
from core.base.model.Manager import Manager
from core.base.model.Version import Version
from core.commons import constants
from core.util.Decorators import Online


class SkillStoreManager(Manager):
	STORE_URLS = {
		'master': ['http://skills.projectalice.io/assets/store/master.json', dict()],
		'rc'    : ['http://skills.projectalice.io/assets/store/rc.json', dict()],
		'beta'  : ['http://skills.projectalice.io/assets/store/beta.json', dict()],
		'alpha' : ['http://skills.projectalice.io/assets/store/alpha.json', dict()]
	}


	def onStart(self):
		self._refreshStoreData()


	@Online
	def onQuarterHour(self):
		self._refreshStoreData()


	def _refreshStoreData(self):
		for releaseType, data in self.STORE_URLS.items():
			url = data[0]

			req = requests.get(url)
			if req.status_code not in {200, 304}:
				return

			self.STORE_URLS[releaseType][1] = json.loads(req.content)


	def getStoreData(self, releaseType: str) -> dict:
		return self.STORE_URLS[releaseType][1]


	def getSkillUpdateVersion(self, skillName: str, releaseType: str = None) -> Optional[tuple]:
		releaseType = releaseType or self.ConfigManager.getAliceConfigByName('skillsUpdateChannel')
		versionMapping = self.getStoreData(releaseType).get(skillName, dict()).get('versionMapping', dict)

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
				skillUpdateVersion = (repoVersion, str(aliceMinVersion))

		if not skillUpdateVersion[0].isVersionNumber:
			raise GithubNotFound

		return skillUpdateVersion


	def getSkillData(self, skillName: str, releaseType: str) -> dict:
		releaseType = releaseType or self.ConfigManager.getAliceConfigByName('skillsUpdateChannel')
		return self.getStoreData(releaseType).get(skillName, dict())
