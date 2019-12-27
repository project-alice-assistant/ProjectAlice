from pathlib import Path

import requests
import shutil
from zipfile import ZipFile
from io import BytesIO

from core.base.model.ProjectAliceObject import ProjectAliceObject


class SkillStore(ProjectAliceObject):

	def __init__(self):
		super().__init__(logDepth=3)
		self._availableSkills = dict()
		self._userUpdatePref = None
		self._updateBranch = None
		self.updateSkillsUpdateBranch()
		self.updateSkillStore()


	def updateSkillsUpdateBranch(self):
		userUpdatePref = self.ConfigManager.getAliceConfigByName('updateChannel')
		if userUpdatePref == self._userUpdatePref:
			return

		self._userUpdatePref = userUpdatePref

		if userUpdatePref == 'master':
			self._updateBranch = 'master'
			return

		req = requests.get('https://api.github.com/repos/project-alice-assistant/ProjectAliceSkills/branches')
		result = req.json()
		if not result:
			self.logError('Failed to retrieve available branches from GitHub')
			return

		versions = list()
		for branch in result:
			repoVersion = Version(branch['name'])
			if not repoVersion.isVersionNumber:
				continue

			releaseType = repoVersion.infos['releaseType']
			if userUpdatePref == 'alpha' and releaseType in ('master', 'rc', 'b', 'a') \
				or userUpdatePref == 'beta' and releaseType in ('master', 'rc', 'b') \
				or userUpdatePref == 'rc' and releaseType in ('master', 'rc'):
				versions.append(repoVersion)

		if not versions:
			self.logError('Could not retrieve a matching version from GitHub')
			return
		
		versions.sort(reverse=True)
		self._updateBranch = versions[0]


	def updateSkillStore(self) -> bool:
		self.logInfo('Updating Skill Store')

		installers = dict()
		req = requests.get(url=f'https://skills.projectalice.io/assets/{self._updateBranch}/store/store.json')
		results = req.json()

		if not results:
			return False

		for skill in results:
			if 'lang' not in skill['conditions']:
				skill['conditions']['lang'] = constants.ALL
			installers[skill['name']] = skill

		aliceVersion = Version(constants.VERSION)
		activeLanguage = self.LanguageManager.activeLanguage.lower()
		self._availableSkills = {
			skillName: skillInfo for skillName, skillInfo in installers.items()
			if aliceVersion >= Version(skillInfo['aliceMinVersion'])
			  and (activeLanguage in skillInfo['conditions']['lang'] or skillInfo['conditions']['lang'] == constants.ALL)
		}
		return True


	@property
	def availableSkills(self) -> dict:
		return self._availableSkills


	@property
	def updateBranch(self) -> str:
		return self._updateBranch


	def installSkill(self, skillName: str, dest: Path) -> bool:
		skillUrl = f'https://skills.projectalice.io/assets/{self._updateBranch}/skills/{skillName}.zip'

		try:
			zipDownload = requests.get(skillUrl)
			zipDownload.raise_for_status()
			
		except requests.exceptions.RequestException as e:
			self.logError(f'Error downloading skill: {e}')
			return False

		zipFile = ZipFile(BytesIO(zipDownload.content))

		if dest.exists():
			self._cleanSkillDir(dest)

	    zipFile.extractall(dest)
		return True


	def _cleanSkillDir(self, dest: Path):
		filesToDelete = list()
		directoriesToDelete = list()
		for file in dest.iterdir():
			if file.with_suffix(file.suffix + '.template').exists() or file.with_suffix(file.suffix + '.dist').exists() or file.suffix == '.conf':
				continue

			if (file.is_dir() and not file.name.startswith('_')) or file.name == '__pycache__':
				directoriesToDelete.append(file)

			elif file.is_file():
				filesToDelete.append(file)

		# Not deleting directories and files directly because they are needed for the .dist check
		for directory in directoriesToDelete:
			shutil.rmtree(directory)

		for file in filesToDelete:
			file.unlink()


	def checkForSkillUpdate(self, skillToCheck: str = None) -> bool:
		if self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			return False

		self.logInfo('Checking for skill updates')

		if not self.InternetManager.online:
			self.logInfo('Not connected...')
			return False

		if not self.updateSkillStore():
			self.logInfo('Failed retrieving updates for the skill store')
			return False

		installedSkill = self.ConfigManager.skillsConfigurations.get(skillName)
		if not installedSkill:
			return False

		remoteSkill = self._availableSkills.get(skillToCheck)
		if not remoteSkill:
			self.logInfo(f'❓ Skill "{skillToCheck}" is not available in the skill store. Deprecated or is it a dev skill?')
			return False

		if Version(installedSkill['version']) >= Version(remoteSkill['version']):
			self.logInfo(f'✔ {skillToCheck} - Version {skillToCheck["version"]} in {self._userUpdatePref}')
			return False

		self.logInfo(f'❌ {skillToCheck} - Version {skillToCheck["version"]} < {remoteSkill["version"]} in {self._userUpdatePref}')
		return True
