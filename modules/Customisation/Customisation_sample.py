# -*- coding: utf-8 -*-

from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession


class Customisation(Module):
	"""
		You can use this class to override anything any module do. Want something happening when you are going bed? Override onGoingBed!
	"""
	MODULE_NAME = 'Customisation'


	def __init__(self):
		self._SUPPORTED_INTENTS = list()

		super().__init__(self._SUPPORTED_INTENTS)


	def onMessage(self, intent: str, session: DialogSession) -> bool:
		if not self.filterIntent(intent, session):
			return False

		siteId = session.siteId
		slots = session.slots
		sessionId = session.slotsAsObjects
		customData = session.customData
		payload = session.payload

		return True
