from pathlib import Path

import requests
import shutil

from core.ProjectAliceExceptions import GithubNotFound, GithubRateLimit, GithubTokenFailed
from core.base.SuperManager import SuperManager
from core.base.model.ProjectAliceObject import ProjectAliceObject


class GithubCloner(ProjectAliceObject):

	NAME = 'GithubCloner'

	def __init__(self, baseUrl: str, path: Path, dest: Path):
		super().__init__(logDepth=3)
		self._baseUrl = baseUrl
		self._path = path
		self._dest = dest


	@classmethod
	def getGithubAuth(cls) -> tuple:
		username = SuperManager.getInstance().configManager.getAliceConfigByName('githubUsername')
		token = SuperManager.getInstance().configManager.getAliceConfigByName('githubToken')
		return (username, token) if (username and token) else None


	def clone(self, skillName: str, api: bool = False) -> bool:
		if not self._dest.exists():
			self._dest.mkdir(parents=True)
		elif api:
			self._cleanDestDir()
		else:
			if Path(self._dest / '.git').exists():
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'stash'])
			else:
				shutil.rmtree(str(self._dest))
				self._dest.mkdir(parents=True)

		try:
			if api:
				return self._doApiClone(f'https://api.github.com/{self._baseUrl}/{self._path}?ref={self.ConfigManager.getSkillsUpdateTag(skillName)}')
			else:
				return self._doClone(skillName)

		except Exception:
			return False


	def _doClone(self, skillName: str) -> bool:
		try:
			if not Path(self._dest / '.git').exists():
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'init'])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'remote', 'add', 'origin', self._baseUrl])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'pull'])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'checkout', str(self.ConfigManager.getSkillsUpdateTag(skillName))])
			else:
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'pull'])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'checkout', str(self.ConfigManager.getSkillsUpdateTag(skillName))])
				self.Commons.runSystemCommand(['git', '-C', str(self._dest), 'stash', 'clear'])

			return True
		except Exception as e:
			self.logWarning(f'Something went wrong cloning github repo: {e}')
			return False


	def _doApiClone(self, url: str):
		try:
			req = requests.get(url, auth=self.getGithubAuth())
			if req.status_code == 401:
				raise GithubTokenFailed
			elif req.status_code == 403:
				raise GithubRateLimit
			elif req.status_code == 404:
				raise GithubNotFound
			elif req.status_code != 200:
				raise Exception

			data = req.json()
			for item in data:
				path = Path(*Path(item['path']).parts[3:])
				if item['type'] == 'file':
					if path.suffix == '.install':
						continue

					fileStream = requests.get(url=item['download_url'], auth=self.getGithubAuth())
					Path(self._dest / path).write_bytes(fileStream.content)
				else:
					Path(self._dest / path).mkdir(parents=True)
					self._doApiClone(url=item['url'])

		except GithubTokenFailed:
			self.logError('Provided Github username / token invalid')
			raise

		except GithubRateLimit:
			self.logError('Github rate limit reached, cannot access updates for now. You should consider creating a token to avoid this problem')
			raise

		except GithubNotFound:
			self.logError('Requested skill not found on servers')
			raise

		except Exception as e:
			self.logError(f'Error downloading skill: {e}')
			raise


	def _cleanDestDir(self):
		filesToDelete = list()
		directoriesToDelete = list()
		for file in self._dest.iterdir():
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
