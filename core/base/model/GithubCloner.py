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
#  Last modified: 2021.08.21 at 12:56:45 CEST

import json
import requests
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


	@classmethod
	def hasAuth(cls) -> bool:
		"""
		Returns if the user has entered the github data for authentification
		:return:
		"""
		return cls.getGithubAuth() is not None


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


	def checkOwnRepoAvailable(self, skillName: str) -> bool:
		"""
		check if a repository for the given skill name exists in the users github
		:param skillName:
		:return:
		"""
		req = requests.get(f'https://api.github.com/repos/{self.getGithubAuth()[0]}/skill_{skillName}', auth=GithubCloner.getGithubAuth())
		if req.status_code != 200:
			self.logInfo("Couldn't find repository on github")
			return False
		return True


	def createForkForSkill(self, skillName: str) -> bool:
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
			self.logError("Couldn't create fork for repository!")


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

			remote = f'https://{self.ConfigManager.getAliceConfigByName("githubUsername")}:{self.ConfigManager.getAliceConfigByName("githubToken")}@github.com/{self.ConfigManager.getAliceConfigByName("githubUsername")}/skill_{skillName}.git'
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'remote', 'add', 'AliceSK', remote])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'checkout', 'master'])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'branch', '--set-upstream-to=AliceSK/master'])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'pull'])

			return True
		except Exception as e:
			self.logWarning(f'Something went wrong cloning github repo: {e}')
			return False


	def checkoutMaster(self) -> bool:
		"""
		set upstream to origin/master
		:param skillName:
		:return:
		"""
		try:
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'branch', '--set-upstream-to=origin/master'])
			return True
		except Exception as e:
			self.logWarning(f'Something went wrong cloning github repo: {e}')
			return False


	def gitDefaults(self) -> bool:
		try:
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'config', 'user.email', self.ConfigManager.getAliceConfigByName('githubMail') or 'githubbot@projectalice.io'])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'config', 'user.name', self.ConfigManager.getAliceConfigByName('githubUsername') or 'ProjectAliceBot'])
			return True
		except Exception as e:
			self.logWarning(f'Something went wrong cloning github repo: {e}')
			return False


	def gitPush(self) -> bool:
		"""
		add all changes to git, commit and push to AliceSK upstream
		:return:
		"""
		try:
			self.gitDefaults()
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'add', '.'])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'commit', '-m', 'pushed by AliceSK'])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'push', '--set-upstream', 'AliceSK', 'master'])
			return True
		except Exception as e:
			self.logWarning(f'Something went wrong cloning github repo: {e}')
			return False
