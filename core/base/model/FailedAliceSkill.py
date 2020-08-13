from __future__ import annotations

import json

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession


class FailedAliceSkill(ProjectAliceObject):


	def __init__(self, installer: dict):
		self._installer = installer
		self._updateAvailable = False
		self._name = installer['name']
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
		return json.dumps(self.toJson())


	def __str__(self) -> str:
		return self.__repr__()


	def toJson(self) -> dict:
		return {
			'name'           : self._name,
			'author'         : self._installer['author'],
			'version'        : self._installer['version'],
			'updateAvailable': self._updateAvailable
		}
