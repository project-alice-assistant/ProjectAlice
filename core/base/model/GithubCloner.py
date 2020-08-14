from pathlib import Path

import shutil

from core.base.SuperManager import SuperManager
from core.base.model.ProjectAliceObject import ProjectAliceObject


class GithubCloner(ProjectAliceObject):
	NAME = 'GithubCloner'


	def __init__(self, baseUrl: str, path: Path, dest: Path):
		super().__init__()
		self._baseUrl = baseUrl
		self._path = path
		self._dest = dest


	@classmethod
	def getGithubAuth(cls) -> tuple:
		username = SuperManager.getInstance().configManager.getAliceConfigByName('githubUsername')
		token = SuperManager.getInstance().configManager.getAliceConfigByName('githubToken')
		return (username, token) if (username and token) else None


	def clone(self, skillName: str) -> bool:
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
		try:
			if not Path(self._dest / '.git').exists():
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'init'])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'remote', 'add', 'origin', self._baseUrl])

			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'pull', 'origin', 'master'])
			self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'checkout', self.SkillStoreManager.getSkillUpdateTag(skillName)])

			return True
		except Exception as e:
			self.logWarning(f'Something went wrong cloning github repo: {e}')
			return False
