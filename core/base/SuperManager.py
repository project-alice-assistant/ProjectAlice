from __future__ import annotations

import logging

from core.commons import constants


class SuperManager(object):

	NAME        = 'SuperManager'
	_INSTANCE   = None


	def __new__(cls, *args, **kwargs):
		if not isinstance(SuperManager._INSTANCE, SuperManager):
			SuperManager._INSTANCE = object.__new__(cls)

		return SuperManager._INSTANCE


	def __init__(self, mainClass):
		self._logger                   = logging.getLogger('ProjectAlice')

		SuperManager._INSTANCE         = self
		self._managers                 = dict()

		self.projectAlice              = mainClass
		self.configManager             = None
		self.databaseManager           = None
		self.languageManager           = None
		self.snipsServicesManager      = None
		self.ASRManager                = None
		self.TTSManager                = None
		self.protectedIntentManager    = None
		self.threadManager             = None
		self.mqttManager               = None
		self.timeManager               = None
		self.dialogSessionManager      = None
		self.multiIntentManager        = None
		self.telemetryManager          = None
		self.moduleManager             = None
		self.deviceManager             = None
		self.internetManager           = None
		self.snipsConsoleManager       = None
		self.samkillaManager           = None
		self.wakewordManager           = None
		self.userManager               = None
		self.talkManager               = None
		self.webInterfaceManager       = None


	def onStart(self):
		configManager = self._managers.pop('ConfigManager')
		configManager.onStart()

		snipsServicesManager = self._managers.pop('SnipsServicesManager')
		snipsServicesManager.onStart()

		databaseManager = self._managers.pop('DatabaseManager')
		databaseManager.onStart()

		userManager = self._managers.pop('UserManager')
		userManager.onStart()

		mqttManager = self._managers.pop('MqttManager')
		mqttManager.onStart()

		languageManager = self._managers.pop('LanguageManager')
		languageManager.onStart()

		talkManager = self._managers.pop('TalkManager')
		moduleManager = self._managers.pop('ModuleManager')

		samkillaManager = self._managers.pop('SamkillaManager')

		for manager in self._managers.values():
			if manager:
				manager.onStart()

		talkManager.onStart()
		moduleManager.onStart()
		samkillaManager.onStart()

		self._managers[configManager.name] = configManager
		self._managers[languageManager.name] = languageManager
		self._managers[talkManager.name] = talkManager
		self._managers[snipsServicesManager.name] = snipsServicesManager
		self._managers[databaseManager.name] = databaseManager
		self._managers[userManager.name] = userManager
		self._managers[mqttManager.name] = mqttManager
		self._managers[moduleManager.name] = moduleManager
		self._managers[samkillaManager.name] = samkillaManager


	def onBooted(self):
		for manager in self._managers.values():
			if manager:
				manager.onBooted()


	@staticmethod
	def getInstance() -> SuperManager:
		return SuperManager._INSTANCE


	def initManagers(self):
		from core.base.ConfigManager            import ConfigManager
		from core.base.ModuleManager            import ModuleManager
		from core.device.DeviceManager          import DeviceManager
		from core.dialog.DialogSessionManager   import DialogSessionManager
		from core.dialog.MultiIntentManager     import MultiIntentManager
		from core.dialog.ProtectedIntentManager import ProtectedIntentManager
		from core.server.MqttManager            import MqttManager
		from core.snips.SamkillaManager         import SamkillaManager
		from core.snips.SnipsConsoleManager     import SnipsConsoleManager
		from core.snips.SnipsServicesManager    import SnipsServicesManager
		from core.user.UserManager              import UserManager
		from core.util.DatabaseManager          import DatabaseManager
		from core.util.InternetManager          import InternetManager
		from core.util.TelemetryManager         import TelemetryManager
		from core.util.ThreadManager            import ThreadManager
		from core.util.TimeManager              import TimeManager
		from core.voice.ASRManager              import ASRManager
		from core.voice.LanguageManager         import LanguageManager
		from core.voice.TalkManager             import TalkManager
		from core.voice.TTSManager              import TTSManager
		from core.voice.WakewordManager         import WakewordManager
		from core.interface.WebInterfaceManager import WebInterfaceManager

		self.configManager              = ConfigManager()
		self.databaseManager            = DatabaseManager()
		self.languageManager            = LanguageManager()
		self.snipsServicesManager       = SnipsServicesManager()
		self.ASRManager                 = ASRManager()
		self.TTSManager                 = TTSManager()
		self.threadManager              = ThreadManager()
		self.protectedIntentManager     = ProtectedIntentManager()
		self.mqttManager                = MqttManager()
		self.timeManager                = TimeManager()
		self.userManager                = UserManager()
		self.dialogSessionManager       = DialogSessionManager()
		self.multiIntentManager         = MultiIntentManager()
		self.telemetryManager           = TelemetryManager()
		self.moduleManager              = ModuleManager()
		self.deviceManager              = DeviceManager()
		self.internetManager            = InternetManager()
		self.snipsConsoleManager        = SnipsConsoleManager()
		self.samkillaManager            = SamkillaManager()
		self.wakewordManager            = WakewordManager()
		self.talkManager                = TalkManager()
		self.webInterfaceManager        = WebInterfaceManager()

		self._managers = {name[0].upper() + name[1:]: manager for name, manager in self.__dict__.items() if name.endswith('Manager')}


	def broadcast(self, method, exceptions: list = None, manager = None, propagateToModules: bool = False, silent: bool = False, args: list = None):
		if not exceptions and not manager:
			self._logger.warning(f'[{self.NAME}] Cannot broadcast to itself, the calling method has to be put in exceptions')

		if 'ProjectAlice' not in exceptions:
			exceptions.append('ProjectAlice')

		if not args:
			args = list()

		deadManagers = list()
		for name in self._managers:
			man = self._managers[name]

			if not man:
				deadManagers.append(name)
				continue

			if (manager and man.name != manager.name) or man.name in exceptions:
				continue

			try:
				func = getattr(man, method)
				func(*args)
			except AttributeError as e:
				if not silent:
					self._logger.warning(f"[{self.NAME}] Couldn't find method {method} in manager {man.name}: {e}")

		if propagateToModules:
			self.moduleManager.broadcast(method=method, silent=silent, args=args)

		for name in deadManagers:
			del self._managers[name]


	def onStop(self):
		managerName = constants.UNKNOWN_MANAGER
		try:
			for managerName, manager in self._managers.items():
				manager.onStop()
		except Exception as e:
			self._logger.info(f'[{self.NAME}] Error while shutting down manager "{managerName}": {e}')


	def getManager(self, managerName: str):
		return self._managers.get(managerName, None)