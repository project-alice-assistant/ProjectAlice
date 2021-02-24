from __future__ import annotations

import json

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession
from core.base.model.Version import Version
from core.commons import constants


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


	def toDict(self) -> dict:
		return {
			'name'           : self._name,
			'author'         : self._installer['author'],
			'version'        : self._installer['version'],
			'updateAvailable': self._updateAvailable,
			'maintainers'    : self._maintainers,
			'settings'       : self.ConfigManager.getSkillConfigs(self._name),
			'icon'            : self._icon,
			'description'     : self._description,
			'category'        : self._category,
			'aliceMinVersion' : str(self._aliceMinVersion)
		}
