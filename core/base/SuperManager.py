from __future__ import annotations

from core.commons import constants
from core.util.model.Logger import Logger


class SuperManager:
	NAME = 'SuperManager'
	_INSTANCE = None


	def __new__(cls, *args, **kwargs):
		if not isinstance(SuperManager._INSTANCE, SuperManager):
			SuperManager._INSTANCE = object.__new__(cls)

		return SuperManager._INSTANCE


	def __init__(self, mainClass):
		SuperManager._INSTANCE = self
		self._managers = dict()

		self.projectAlice = mainClass
		self.commons = None
		self.commonsManager = None
		self.configManager = None
		self.databaseManager = None
		self.languageManager = None
		self.asrManager = None
		self.ttsManager = None
		self.protectedIntentManager = None
		self.threadManager = None
		self.mqttManager = None
		self.timeManager = None
		self.multiIntentManager = None
		self.telemetryManager = None
		self.skillManager = None
		self.deviceManager = None
		self.locationManager = None
		self.internetManager = None
		self.wakewordRecorder = None
		self.userManager = None
		self.talkManager = None
		self.webInterfaceManager = None
		self.nodeRedManager = None
		self.skillStoreManager = None
		self.nluManager = None
		self.dialogTemplateManager = None
		self.aliceWatchManager = None
		self.audioManager = None
		self.dialogManager = None
		self.locationManager = None
		self.wakewordManager = None
		self.assistantManager = None


	def onStart(self):
		commons = self._managers.pop('CommonsManager')
		commons.onStart()

		configManager = self._managers.pop('ConfigManager')
		configManager.onStart()

		languageManager = self._managers.pop('LanguageManager')
		languageManager.onStart()

		audioServer = self._managers.pop('AudioManager')
		audioServer.onStart()

		internetManager = self._managers.pop('InternetManager')
		internetManager.onStart()

		databaseManager = self._managers.pop('DatabaseManager')
		databaseManager.onStart()

		userManager = self._managers.pop('UserManager')
		userManager.onStart()

		mqttManager = self._managers.pop('MqttManager')
		mqttManager.onStart()

		talkManager = self._managers.pop('TalkManager')
		skillManager = self._managers.pop('SkillManager')
		assistantManager = self._managers.pop('AssistantManager')
		dialogTemplateManager = self._managers.pop('DialogTemplateManager')
		nluManager = self._managers.pop('NluManager')
		nodeRedManager = self._managers.pop('NodeRedManager')

		for manager in self._managers.values():
			if manager:
				manager.onStart()

		talkManager.onStart()
		nluManager.onStart()
		skillManager.onStart()
		dialogTemplateManager.onStart()
		assistantManager.onStart()
		nodeRedManager.onStart()

		self._managers[configManager.name] = configManager
		self._managers[audioServer.name] = audioServer
		self._managers[languageManager.name] = languageManager
		self._managers[talkManager.name] = talkManager
		self._managers[databaseManager.name] = databaseManager
		self._managers[userManager.name] = userManager
		self._managers[mqttManager.name] = mqttManager
		self._managers[skillManager.name] = skillManager
		self._managers[dialogTemplateManager.name] = dialogTemplateManager
		self._managers[assistantManager.name] = assistantManager
		self._managers[nluManager.name] = nluManager
		self._managers[internetManager.name] = internetManager
		self._managers[nodeRedManager.name] = nodeRedManager


	def onBooted(self):
		for manager in self._managers.values():
			if manager:
				manager.onBooted()

		self.threadManager.doLater(interval=0.5, func=self.mqttManager.playSound, kwargs={'soundFilename': 'boot'})


	@staticmethod
	def getInstance() -> SuperManager:
		return SuperManager._INSTANCE


	def initManagers(self):
		from core.commons.CommonsManager import CommonsManager
		from core.base.ConfigManager import ConfigManager
		from core.base.SkillManager import SkillManager
		from core.device.DeviceManager import DeviceManager
		from core.device.LocationManager import LocationManager
		from core.dialog.MultiIntentManager import MultiIntentManager
		from core.dialog.ProtectedIntentManager import ProtectedIntentManager
		from core.server.MqttManager import MqttManager
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
		from core.voice.WakewordRecorder import WakewordRecorder
		from core.interface.WebInterfaceManager import WebInterfaceManager
		from core.interface.NodeRedManager import NodeRedManager
		from core.base.SkillStoreManager import SkillStoreManager
		from core.dialog.DialogTemplateManager import DialogTemplateManager
		from core.base.AssistantManager import AssistantManager
		from core.nlu.NluManager import NluManager
		from core.util.AliceWatchManager import AliceWatchManager
		from core.server.AudioServer import AudioManager
		from core.dialog.DialogManager import DialogManager
		from core.voice.WakewordManager import WakewordManager

		self.commonsManager = CommonsManager()
		self.commons = self.commonsManager
		self.configManager = ConfigManager()
		self.audioManager = AudioManager()
		self.databaseManager = DatabaseManager()
		self.languageManager = LanguageManager()
		self.asrManager = ASRManager()
		self.ttsManager = TTSManager()
		self.threadManager = ThreadManager()
		self.protectedIntentManager = ProtectedIntentManager()
		self.mqttManager = MqttManager()
		self.timeManager = TimeManager()
		self.userManager = UserManager()
		self.multiIntentManager = MultiIntentManager()
		self.telemetryManager = TelemetryManager()
		self.skillManager = SkillManager()
		self.deviceManager = DeviceManager()
		self.locationManager = LocationManager()
		self.internetManager = InternetManager()
		self.wakewordRecorder = WakewordRecorder()
		self.talkManager = TalkManager()
		self.webInterfaceManager = WebInterfaceManager()
		self.nodeRedManager = NodeRedManager()
		self.skillStoreManager = SkillStoreManager()
		self.dialogTemplateManager = DialogTemplateManager()
		self.assistantManager = AssistantManager()
		self.nluManager = NluManager()
		self.aliceWatchManager = AliceWatchManager()
		self.dialogManager = DialogManager()
		self.wakewordManager = WakewordManager()

		self._managers = {name[0].upper() + name[1:]: manager for name, manager in self.__dict__.items() if name.endswith('Manager')}


	def onStop(self):
		managerName = constants.UNKNOWN_MANAGER
		mqttManager = self._managers.pop('MqttManager')
		try:
			for managerName, manager in self._managers.items():
				manager.onStop()

			managerName = mqttManager.name
			mqttManager.onStop()
		except Exception as e:
			Logger().logError(f'Error while shutting down manager **{managerName}**: {e}')
			import traceback
			traceback.print_exc()


	def getManager(self, managerName: str):
		return self._managers.get(managerName, None)


	def restartManager(self, manager: str):
		if not manager in self._managers:
			Logger().logWarning(f'Was asking to restart manager **{manager}** but it doesn\'t exist')
			return

		self._managers[manager].onStop()
		self._managers[manager].onStart()
		self._managers[manager].onBooted()


	@property
	def managers(self) -> dict:
		return self._managers
