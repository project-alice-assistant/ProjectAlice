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

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.base.model.Version import Version
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class FailedAliceSkill(ProjectAliceObject):


	def __init__(self, installer: dict):
		self._installer = installer
		self._updateAvailable = False
		self._name = installer['name']
		self._modified = False
		self._icon = self._installer.get('icon', 'fas fa-biohazard')
		self._aliceMinVersion = Version.fromString(self._installer.get('aliceMinVersion', '1.0.0-b4'))
		self._maintainers = self._installer.get('maintainers', list())
		self._description = self._installer.get('desc', '')
		self._category = self._installer.get('category', constants.UNKNOWN)
		self._conditions = self._installer.get('conditions', dict())
		self._skillPath = Path('skills') / self._name
		super().__init__()


	@staticmethod
	def onMessageDispatch(_session: DialogSession) -> bool:
		return False


	def onStart(self):
		pass # Is always handeled by the sibling


	def onStop(self):
		pass  # Is always handeled by the sibling


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
		return self._modified


	@modified.setter
	def modified(self, value: bool):
		"""
		As the skill has no writeToDB method and this is the only value that has to be saved right away
		a update of the value on the DB is performed. This should only occure manually triggered when the user starts to make local changes
		:param value:
		:return:
		"""
		self._modified = value
		self.SkillManager.setSkillModified(skillName=self._name, modified=self._modified)
		dbVal = 1 if value else 0
		self.logInfo(f'Wrote dbval {dbVal}')
		self.DatabaseManager.update(tableName=self.SkillManager.DBTAB_SKILLS,
		                            callerName=self.SkillManager.name,
		                            row=('skillname', self._name),
		                            values={'modified': dbVal})


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
			'modified'       : self._modified,
			'updateAvailable': self._updateAvailable,
			'maintainers'    : self._maintainers,
			'settings'       : self.ConfigManager.getSkillConfigs(self._name),
			'icon'           : self._icon,
			'description'    : self._description,
			'category'       : self._category,
			'aliceMinVersion': str(self._aliceMinVersion)
		}
