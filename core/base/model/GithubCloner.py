from pathlib import Path

import requests
import shutil
from zipfile import ZipFile
from io import BytesIO

from core.ProjectAliceExceptions import GithubNotFound, GithubRateLimit, GithubTokenFailed
from core.base.SuperManager import SuperManager
from core.base.model.ProjectAliceObject import ProjectAliceObject


class GithubCloner(ProjectAliceObject):

	NAME = 'GithubCloner'

	def __init__(self, skillName: str, dest: Path):
		super().__init__(logDepth=3)
		self._skillName = skillName
		self._dest = dest


	def clone(self) -> bool:
		if self._dest.exists():
			self._cleanDestDir()

		updateSource = self.ConfigManager.getSkillsUpdateSource()
		skillUrl = f'https://skills.projectalice.io/assets/{updateSource}/skills/{self._skillName}.zip'

		try:
			zipDownload = requests.get(skillUrl)
			zipDownload.raise_for_status()
			
		except requests.exceptions.RequestException as e:
			self.logError(f'Error downloading skill: {e}')
			return False
		
		zipFile = ZipFile(BytesIO(zipDownload.content))
	    zipFile.extractall(dest)
		return True


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
