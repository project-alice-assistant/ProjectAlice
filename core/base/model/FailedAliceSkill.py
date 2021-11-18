#  Copyright (c) 2021
#
#  This file, FailedAliceSkill.py, is part of Project Alice.
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

from __future__ import annotations

import json
from pathlib import Path

from AliceGit.Git import Repository
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.base.model.Version import Version
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class FailedAliceSkill(ProjectAliceObject):

	def __init__(self, installer: dict):
		self._installer = installer
		self._updateAvailable = False
		self._name = installer['name']
		self._icon = self._installer.get('icon', 'fas fa-biohazard')
		self._aliceMinVersion = Version.fromString(self._installer.get('aliceMinVersion', '1.0.0-b4'))
		self._maintainers = self._installer.get('maintainers', list())
		self._description = self._installer.get('desc', '')
		self._category = self._installer.get('category', constants.UNKNOWN)
		self._conditions = self._installer.get('conditions', dict())
		self._skillPath = Path('skills') / self._name
		self._repository = Repository(directory=self._skillPath, init=True, raiseIfExisting=False)
		super().__init__()


	@staticmethod
	def onMessageDispatch(_session: DialogSession) -> bool:
		return False


	def onStart(self):
		pass  # Is always handled by the sibling


	def onStop(self):
		pass  # Is always handled by the sibling


	def onBooted(self) -> bool:
		return True


	def onSkillInstalled(self, **kwargs):
		self._updateAvailable = False


	def onSkillUpdated(self, **kwargs):
		self._updateAvailable = False


	def __repr__(self) -> str:
		return json.dumps(self.toDict())


	def __str__(self) -> str:
		return self.__repr__()


	@property
	def modified(self) -> bool:
		return self._repository.isDirty()


	@property
	def repository(self) -> Repository:
		return self._repository


	@property
	def skillPath(self) -> Path:
		return self._skillPath


	def getResource(self, resourcePathFile: str = '') -> Path:
		return self.skillPath / resourcePathFile


	def toDict(self) -> dict:
		return {
			'name'           : self._name,
			'author'         : self._installer['author'],
			'version'        : self._installer['version'],
			'modified'       : self.modified,
			'updateAvailable': self._updateAvailable,
			'maintainers'    : self._maintainers,
			'settings'       : self.ConfigManager.getSkillConfigs(self._name),
			'icon'           : self._icon,
			'description'    : self._description,
			'category'       : self._category,
			'aliceMinVersion': str(self._aliceMinVersion)
		}
