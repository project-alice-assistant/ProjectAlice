# -*- coding: utf-8 -*-

from collections import OrderedDict
from threading import Timer

from core.base.ConfigManager import ConfigManager
from core.base.Manager import Manager
from core.base.ModuleManager import ModuleManager
from core.server.MqttServer import MqttServer
from core.dialog.MultiIntentManager import MultiIntentManager
from core.dialog.ProtectedIntentManager import ProtectedIntentManager
from core.voice.TalkManager import TalkManager
from core.dialog.DialogSessionManager import DialogSessionManager
from core.util.ThreadManager import ThreadManager
from core.util.TimeManager import TimeManager
from core.user.UserManager import UserManager


class SuperManager(Manager):

	NAME = 'SuperManager'
	INSTANCE = None

	def __init__(self, mainClass):
		Manager.__init__(self, mainClass, self.NAME)

		if not self.INSTANCE:
			self.INSTANCE = self
		else:
			self._logger.error("Trying to instanciate {} but instance already existing".format(self.NAME))

		managers = {
			ConfigManager.NAME					: ConfigManager(self),
			UserManager.NAME 					: UserManager(self),
			ThreadManager.NAME 					: ThreadManager(self),
			ProtectedIntentManager.NAME 		: ProtectedIntentManager(self),
			MqttServer.NAME 					: MqttServer(self),
			TimeManager.NAME 					: TimeManager(self),
			TalkManager.NAME 					: TalkManager(self),
			DialogSessionManager.NAME 			: DialogSessionManager(self),
			MultiIntentManager.NAME 			: MultiIntentManager(self),
			ModuleManager.NAME 					: ModuleManager(self)
		}
		self._managers = OrderedDict(managers)


	@property
	def ConfigManager(self):
		return self._managers[ConfigManager.NAME]

	@property
	def ThreadManager(self):
		return self._managers[ThreadManager.NAME]

	@property
	def ProtectedIntentManager(self):
		return self._managers[ProtectedIntentManager.NAME]

	@property
	def MqttServer(self):
		return self._managers[MqttServer.NAME]

	@property
	def TimeManager(self):
		return self._managers[TimeManager.NAME]

	@property
	def TalkManager(self):
		return self._managers[TalkManager.NAME]

	@property
	def UserManager(self):
		return self._managers[UserManager.NAME]

	@property
	def DialogSessionManager(self):
		return self._managers[DialogSessionManager.NAME]

	@property
	def MultiIntentManager(self):
		return self._managers[MultiIntentManager.NAME]

	@property
	def ModuleManager(self):
		return self._managers[ModuleManager.NAME]


	def broadcast(self, method, manager = None, exceptions = None):
		if not exceptions:
			exceptions = list()

		if not manager:
			for man in self._managers:
				if not man:
					self._logger.warning('Tried to broadcast to a None manager')
					Timer(interval = 10, function = self.broadcast, args=[method, man, exceptions])
					continue

				if man.NAME in exceptions:
					continue

				try:
					func = getattr(man, method)
					func()
				except:
					self._logger.warning("Couldn't find method {} in manager {}".format(method, man.NAME))
		else:
			if manager.NAME in exceptions:
				return

			try:
				func = getattr(manager, method)
				func()
			except:
				self._logger.warning("Couldn't find method {} in manager {}".format(method, manager.NAME))


	def registerManager(self, manager):
		if manager.NAME not in self._managers:
			self._managers[manager.NAME] = manager


	def getManager(self, managerName):
		if managerName not in self._managers:
			self._logger.error('{} not found in manager list'.format(managerName))
			return None
		return self._managers[managerName]


	def onStart(self):
		for manager in self._managers.values():
			manager.onStart()


	def onStop(self):
		for manager in self._managers.values():
			manager.onStop()
