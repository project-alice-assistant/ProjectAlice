#  Copyright (c) 2021
#
#  This file, GithubCloner.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:45 CEST

import shutil
from pathlib import Path

from core.base.SuperManager import SuperManager
from core.base.model.ProjectAliceObject import ProjectAliceObject


class GithubCloner(ProjectAliceObject):
	NAME = 'GithubCloner'


	def __init__(self, baseUrl: str, dest: Path):
		super().__init__()
		self._baseUrl = baseUrl
		self._dest = dest


	@classmethod
	def getGithubAuth(cls) -> tuple:
		"""
		Returns the users configured username and token for github as a tuple
		When one of the values is not supplied None is returned.
		:return:
		"""
		username = SuperManager.getInstance().configManager.getAliceConfigByName('githubUsername')
		token = SuperManager.getInstance().configManager.getAliceConfigByName('githubToken')
		return (username, token) if (username and token) else None


	def clone(self, skillName: str) -> bool:
		"""
		Clone a skill from github to the skills folder
		This will stash and clean all changes that have been made locally
		:param skillName:
		:return:
		"""
		if not self._dest.exists():
			self._dest.mkdir(parents=True)
		else:
			if Path(self._dest / '.git').exists():
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'stash'])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'clean', '-df'])
			else:
				shutil.rmtree(str(self._dest))
				self._dest.mkdir(parents=True)

		return self._doClone(skillName)


	def _doClone(self, skillName: str) -> bool:
		"""
		internal method to perform the clone of a skill - assumes there are no pending changes
		:param skillName:
		:return:
		"""
		try:
			updateTag = self.SkillStoreManager.getSkillUpdateTag(skillName)
			if not Path(self._dest / '.git').exists():
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'init'])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'remote', 'add', 'origin', self._baseUrl])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'pull'])

			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'checkout', updateTag])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'pull', 'origin', updateTag])

			return True
		except Exception as e:
			self.logWarning(f'Something went wrong cloning github repo: {e}')
			return False


	@classmethod
	def checkOwnRepoAvailable(cls, skillName: str) -> bool:
		"""
		check if a repository for the given skill name exists in the users github
		:param skillName:
		:return:
		"""
		req = requests.get(f'https://api.github.com/repos/{self.ConfigManager.getAliceConfigByName("githubUsername")}/skill_{skillName}', auth=GithubCloner.getGithubAuth())
		if req.status_code != 200:
			cls.logInfo("Couldn't find repository on github")
			return False
		return True


	@classmethod
	def createForkForSkill(cls, skillName: str) -> bool:
		"""
		create a fork of the skill from alice official github to the users github.
		:param skillName:
		:return:
		"""
		data = {
			'owner': self.ConfigManager.getAliceConfigByName("githubUsername"),
			'repo' : f'skill_{skillName}'
		}
		req = requests.post(f'https://api.github.com/repos/project-alice-assistant/skill_{skillName}/forks', data=json.dumps(data), auth=GithubCloner.getGithubAuth())
		if req.status_code != 202:
			cls.logError("Couldn't create fork for repository!")


	def checkoutOwnFork(self, skillName: str) -> bool:
		"""
		Assumes there is already a fork for the current skill on the users repository.
		Clone that repository, set upstream to the original repository.
		Will only work on master!
		:param skillName:
		:return:
		"""
		try:
			if not Path(self._dest / '.git').exists():
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'init'])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'remote', 'add', 'origin', self._baseUrl])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'pull'])

			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'remote', 'add', 'AliceSK', f'https://api.github.com/repos/{self.ConfigManager.getAliceConfigByName("githubUsername")}/skill_{skillName}'])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'checkout', 'master'])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'pull', 'AliceSK', 'master'])

			return True
		except Exception as e:
			self.logWarning(f'Something went wrong cloning github repo: {e}')
			return False
