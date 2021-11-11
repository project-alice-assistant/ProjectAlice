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

import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Callable, List, Union

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


class DirtyRepository(Exception):
	def __init__(self):
		super().__init__(f'The repository is dirty. Either use the force option or stash your changes before trying again')


class Git:

	def __init__(self, directory: Union[str, Path], makeDir: bool = False, init: bool = False, url: str = '', quiet: bool = True):
		if isinstance(directory, str):
			directory = Path(directory)

		if not directory.exists() and not makeDir:
			raise PathNotFoundException(directory)

		if directory.exists() and not Path(directory, '.git').exists() and not init:
			raise NotGitRepository(directory)

		directory.mkdir(parents=True, exist_ok=True)

		isRepository = self.isRepository(directory=directory)
		if init:
			if not isRepository:
				self.execute(f'git init')
			else:
				raise AlreadyGitRepository
		else:
			if not isRepository:
				raise NotGitRepository

		self.path      = directory
		self._quiet    = quiet
		self._url      = url

		tags           = self.execute('git tag')
		self.tags      = set(tags.split('\n'))
		branches       = self.execute('git branch')
		self.branches  = set(branches.split('\n'))


	@classmethod
	def clone(cls, url: str, directory: Union[str, Path], branch: str = 'master', makeDir: bool = False, force: bool = False, quiet: bool = True) -> Git:
		if isinstance(directory, str):
			directory = Path(directory)

		response = requests.get(url)
		if response.status_code != 200:
			raise InvalidUrl(url)

		if not directory.exists() and not makeDir:
			raise PathNotFoundException(directory)

		if cls.isRepository(directory=directory):
			if not force:
				raise AlreadyGitRepository(directory)
			else:
				shutil.rmtree(str(directory), onerror=cls.fixPermissions)

		directory.mkdir(parents=True, exist_ok=True)
		cmd = f'git clone {url} {str(directory)} --branch {branch} --recurse-submodules'
		if quiet:
			cmd = f'{cmd} --quiet'
		subprocess.run(cmd)
		return Git(directory=directory, url=url, quiet=quiet)


	@staticmethod
	def isRepository(directory: Union[str, Path]) -> bool:
		if directory and isinstance(directory, str):
			directory = Path(directory)

		gitDir = directory / '.git'
		if not gitDir.exists():
			return False

		expected = [
			'hooks',
			'info',
			'logs',
			'objects',
			'refs',
			'config',
			'description',
			'HEAD',
			'index',
			'packed-refs'
		]

		for item in expected:
			if not Path(gitDir, item).exists():
				return False
		return True


	def checkout(self, branch: str = 'master', tag: str = '', force: bool = False):
		if tag:
			target = f'tags/{tag} -B Branch_{tag}'
		else:
			target = branch

		if self.isDirty():
			if not force:
				raise DirtyRepository()
			else:
				self.revert()

		self.execute(f'git checkout {target} --recurse-submodules')


	def status(self) -> Status:
		return Status(directory=self.path)


	def isDirty(self) -> bool:
		status = self.status()
		return status.isDirty()


	def revert(self):
		self.restore()
		self.clean()
		self.execute('git checkout HEAD')


	def listStash(self) -> List[str]:
		result = self.execute(f'git stash list')
		return result.split('\n')


	def stash(self) -> int:
		self.execute(f'git stash push {str(self.path)}/')
		return len(self.listStash()) - 1


	def dropStash(self, index: Union[int, str] = -1) -> List[str]:
		if index == 'all':
			self.execute(f'git stash clear')
			return list()
		else:
			self.execute(f'git stash drop {index}')
			return self.listStash()


	def pull(self, force: bool = False):
		if self.isDirty():
			if not force:
				raise DirtyRepository()
			else:
				self.revert()

		self.execute(f'git pull')


	def clean(self, removeUntrackedFiles: bool = True, removeUntrackedDirectory: bool = True):
		options = ''
		if removeUntrackedFiles:
			options += 'f'
		if removeUntrackedDirectory:
			options += 'd'
		if options:
			options = f'-{options}'

		self.execute(f'git clean {options}')


	def restore(self):
		self.execute(f'git restore {str(self.path)}')


	def destroy(self):
		shutil.rmtree(self.path, onerror=self.fixPermissions)


	@staticmethod
	def fixPermissions(func: Callable, path: Path, *_args):
		if not os.access(path, os.W_OK):
			os.chmod(path, stat.S_IWUSR)
			func(path)
		else:
			raise # NOSONAR


	def execute(self, command: str) -> str:
		if not command.startswith('git -C'):
			command = command.replace('git', f'git -C {str(self.path)}', 1)

		if self._quiet:
			command = f'{command} --quiet'

		result = subprocess.run(command.split(), capture_output=True, text=True)
		return result.stdout.strip()


class Status:

	def __init__(self, directory: Union[str, Path]):
		if isinstance(directory, str):
			directory = Path(directory)

		self._status = subprocess.run(f'git -C {str(directory)} status'.split(), capture_output=True, text=True).stdout.strip()


	def isDirty(self):
		return 'working tree clean' not in self._status
