#  Copyright (c) 2021
#
#  This file, Git.py, is part of Project Alice.
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
#  Last modified: 2021.11.10 at 14:35:51 CET
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Union

import requests


class PathNotFoundException(Exception):
	def __init__(self, path: Path):
		super().__init__(f'Path "{path}" does not exist')

class NotGitRepository(Exception):
	def __init__(self, path: Path):
		super().__init__(f'Directory "{path}" is not a git repository')

class AlreadyGitRepository(Exception):
	def __init__(self, path: Path):
		super().__init__(f'Directory "{path}" is already a git repository')

class InvalidUrl(Exception):
	def __init__(self, url: str):
		super().__init__(f'The provided url "{url}" is not valid')


class Git:

	def __init__(self, directory: Union[str, Path], makeDir: bool = False, init: bool = False, url: str = '', quiet: bool = True):
		if directory and isinstance(directory, str):
			directory = Path(directory)

		if not directory.exists() and not makeDir:
			raise PathNotFoundException(directory)

		if directory.exists() and not Path(directory, '.git').exists() and not init:
			raise NotGitRepository(directory)

		directory.mkdir(parents=True, exist_ok=True)

		if not Path(directory, '.git').exists() and not init:
			raise NotGitRepository(directory)

		self.path = directory
		self._quiet = quiet
		self._url = url
		self._tags = set()
		self._branches = set()

		if not Path(directory, '.git').exists():
			self.execute(f'git -C {str(directory)} init')


		tags = self.execute('git tag')
		self._tags = set(tags.split('\n'))
		branches = self.execute('git branch')
		self._branches = set(branches.split('\n'))


	@classmethod
	def clone(cls, url: str, directory: Union[str, Path], branch: str = 'master', makeDir: bool = False, force: bool = False, quiet: bool = True) -> Git:
		if directory and isinstance(directory, str):
			directory = Path(directory)

		response = requests.get(url)
		if response.status_code != 200:
			raise InvalidUrl(url)

		if not directory.exists() and not makeDir:
			raise PathNotFoundException(directory)

		if Path(directory, '.git').exists():
			if not force:
				raise AlreadyGitRepository(directory)
			else:
				shutil.rmtree(str(directory), ignore_errors=True)

		directory.mkdir(parents=True, exist_ok=True)
		cmd = f'git clone {url} {str(directory)} --branch {branch} --recurse-submodules'
		if quiet:
			cmd = f'{cmd} --quiet'
		subprocess.run(cmd)
		return Git(directory=directory, url=url, quiet=quiet)


	def checkout(self, branch: str = 'master', tag: str = '', force: bool = False):
		if tag:
			target = f'tags/{tag} -B Branch_{tag}'
		else:
			target = branch

		self.execute(f'git -C {str(self.path)} checkout {target} --recurse-submodules')


	def execute(self, command: str) -> str:
		if self._quiet:
			command = f'{command} --quiet'
		result = subprocess.run(command.split(), capture_output=True, text=True)
		return result.stdout.strip()


	def status(self) -> Status:
		return Status(directory=self.path)


	def isDirty(self) -> bool:
		status = self.status()
		return status.isDirty()


class Status:

	def __init__(self, directory: Union[str, Path]):
		if directory and isinstance(directory, str):
			directory = Path(directory)

		self._status = subprocess.run(f'git -C {str(directory)} status'.split(), capture_output=True, text=True).stdout.strip()


	def isDirty(self):
		return 'working tree clean' not in self._status
