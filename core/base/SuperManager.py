from __future__ import annotations

from core.commons import constants
from core.util.model.Logger import Logger


class SuperManager(Logger):
	NAME = 'SuperManager'
	_INSTANCE = None


	def __new__(cls, *args, **kwargs):
		if not isinstance(SuperManager._INSTANCE, SuperManager):
			SuperManager._INSTANCE = object.__new__(cls)

		return SuperManager._INSTANCE


	def __init__(self, mainClass):
		super().__init__(depth=3)

		SuperManager._INSTANCE = self
		self._managers = dict()

		self.projectAlice = mainClass
		self.commons = None
		self.commonsManager = None
		self.configManager = None
		self.databaseManager = None
		self.languageManager = None
		self.snipsServicesManager = None
		self.asrManager = None
		self.ttsManager = None
		self.protectedIntentManager = None
		self.threadManager = None
		self.mqttManager = None
		self.timeManager = None
		self.dialogSessionManager = None
		self.multiIntentManager = None
		self.telemetryManager = None
		self.skillManager = None
		self.deviceManager = None
		self.internetManager = None
		self.wakewordManager = None
		self.userManager = None
		self.talkManager = None
		self.webInterfaceManager = None
		self.snipsWatchManager = None
		self.nodeRedManager = None
		self.skillStoreManager = None
		self.nluManager = None


	def onStart(self):
		commons = self._managers.pop('CommonsManager')
		commons.onStart()

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
		skillManager = self._managers.pop('SkillManager')
		nluManager = self._managers.pop('NluManager')
		nodeRedManager = self._managers.pop('NodeRedManager')

		for manager in self._managers.values():
			if manager:
				manager.onStart()

		talkManager.onStart()
		skillManager.onStart()
		nluManager.onStart()
		nodeRedManager.onStart()

		self._managers[configManager.name] = configManager
		self._managers[languageManager.name] = languageManager
		self._managers[talkManager.name] = talkManager
		self._managers[snipsServicesManager.name] = snipsServicesManager
		self._managers[databaseManager.name] = databaseManager
		self._managers[userManager.name] = userManager
		self._managers[mqttManager.name] = mqttManager
		self._managers[skillManager.name] = skillManager
		self._managers[nluManager.name] = nluManager
		self._managers[nodeRedManager.name] = nodeRedManager


	def onBooted(self):
		for manager in self._managers.values():
			if manager:
				manager.onBooted()

		self.mqttManager.playSound(soundFilename='boot')


	@staticmethod
	def getInstance() -> SuperManager:
		return SuperManager._INSTANCE


	def initManagers(self):
		from core.commons.CommonsManager import CommonsManager
		from core.base.ConfigManager import ConfigManager
		from core.base.SkillManager import SkillManager
		from core.device.DeviceManager import DeviceManager
		from core.dialog.DialogSessionManager import DialogSessionManager
		from core.dialog.MultiIntentManager import MultiIntentManager
		from core.dialog.ProtectedIntentManager import ProtectedIntentManager
		from core.server.MqttManager import MqttManager
		from core.snips.SnipsServicesManager import SnipsServicesManager
		from core.user.UserManager import UserManager
		from core.util.DatabaseManager import DatabaseManager
		from core.util.InternetManager import InternetManager
		from core.util.TelemetryManager import TelemetryManager
		from core.util.ThreadManager import ThreadManager
		from core.util.TimeManager import TimeManager
		from core.asr.ASRManager import ASRManager
		from core.voice.LanguageManager import LanguageManager
		from core.voice.TalkManager import TalkManager
		from core.voice.TTSManager import TTSManager
		from core.voice.WakewordManager import WakewordManager
		from core.interface.WebInterfaceManager import WebInterfaceManager
		from core.snips.SnipsWatchManager import SnipsWatchManager
		from core.interface.NodeRedManager import NodeRedManager
		from core.base.SkillStoreManager import SkillStoreManager
		from core.nlu.NluManager import NluManager

		self.commonsManager = CommonsManager()
		self.commons = self.commonsManager
		self.configManager = ConfigManager()
		self.databaseManager = DatabaseManager()
		self.languageManager = LanguageManager()
		self.snipsServicesManager = SnipsServicesManager()
		self.asrManager = ASRManager()
		self.ttsManager = TTSManager()
		self.threadManager = ThreadManager()
		self.protectedIntentManager = ProtectedIntentManager()
		self.mqttManager = MqttManager()
		self.timeManager = TimeManager()
		self.userManager = UserManager()
		self.dialogSessionManager = DialogSessionManager()
		self.multiIntentManager = MultiIntentManager()
		self.telemetryManager = TelemetryManager()
		self.skillManager = SkillManager()
		self.deviceManager = DeviceManager()
		self.internetManager = InternetManager()
		self.wakewordManager = WakewordManager()
		self.talkManager = TalkManager()
		self.webInterfaceManager = WebInterfaceManager()
		self.snipsWatchManager = SnipsWatchManager()
		self.nodeRedManager = NodeRedManager()
		self.skillStoreManager = SkillStoreManager()
		self.nluManager = NluManager()

		self._managers = {name[0].upper() + name[1:]: manager for name, manager in self.__dict__.items() if name.endswith('Manager')}


	def onStop(self):
		managerName = constants.UNKNOWN_MANAGER
		try:
			for managerName, manager in self._managers.items():
				manager.onStop()
		except Exception as e:
			self.logError(f'Error while shutting down manager "{managerName}": {e}')


	def getManager(self, managerName: str):
		return self._managers.get(managerName, None)


	@property
	def managers(self) -> dict:
		return self._managers
