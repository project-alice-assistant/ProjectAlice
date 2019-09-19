# -*- coding: utf-8 -*-

from core.base.model.Manager import Manager


class WebInterfaceManager(Manager):
	NAME = 'WebInterfaceManager'

	def __init__(self):
		super().__init__(self.NAME)


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('webInterfaceActive'):
			self._logger.info('[{}] Web interface is disabled by settings'.format(self.name))