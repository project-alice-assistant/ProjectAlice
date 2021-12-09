#  Copyright (c) 2021
#
#  This file, SuperManager.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:46 CEST

from __future__ import annotations

from core.device.model.DeviceAbility import DeviceAbility
from core.util.model.Logger import Logger


class SuperManager(object):
	NAME = 'SuperManager'
	_INSTANCE = None


	def __new__(cls, *args, **kwargs):
		if not isinstance(SuperManager._INSTANCE, SuperManager):
			SuperManager._INSTANCE = object.__new__(cls)

		return SuperManager._INSTANCE


	def __init__(self, mainClass):
		SuperManager._INSTANCE = self
		self._managers = dict()

		self.projectAlice             = mainClass
		self.aliceWatchManager        = None
		self.apiManager               = None
		self.asrManager               = None
		self.assistantManager         = None
		self.audioManager             = None
		self.bugReportManager         = None
		self.commons                  = None
		self.commonsManager           = None
		self.configManager            = None
		self.databaseManager          = None
		self.deviceManager            = None
		self.dialogManager            = None
		self.dialogTemplateManager    = None
		self.internetManager          = None
		self.languageManager          = None
		self.locationManager          = None
		self.locationManager          = None
		self.mqttManager              = None
		self.multiIntentManager       = None
		self.nluManager               = None
		self.nodeRedManager           = None
		self.skillManager             = None
		self.skillStoreManager        = None
		self.stateManager             = None
		self.subprocessManager        = None
		self.talkManager              = None
		self.telemetryManager         = None
		self.threadManager            = None
		self.timeManager              = None
		self.ttsManager               = None
		self.userManager              = None
		self.wakewordManager          = None
		self.wakewordRecorder         = None
		self.webUiManager             = None
		self.webUINotificationManager = None
		self.widgetManager            = None



	def onStart(self):
		try:
			bugReportManager = self._managers.pop('BugReportManager')
			bugReportManager.onStart()
			self._managers[bugReportManager.name] = bugReportManager

			commons = self._managers.pop('CommonsManager')
			commons.onStart()

			stateManager = self._managers.pop('StateManager')
			stateManager.onStart()

			subprocessManager = self._managers.pop('SubprocessManager')
			subprocessManager.onStart()

			configManager = self._managers.pop('ConfigManager')
			configManager.onStart()

			languageManager = self._managers.pop('LanguageManager')
			languageManager.onStart()

			webUINotificationManager = self._managers.pop('WebUINotificationManager')
			webUINotificationManager.onStart()

			locationManager = self._managers.pop('LocationManager')
			locationManager.onStart()

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
			deviceManager = self._managers.pop('DeviceManager')
			widgetManager = self._managers.pop('WidgetManager')
			assistantManager = self._managers.pop('AssistantManager')
			dialogTemplateManager = self._managers.pop('DialogTemplateManager')
			nluManager = self._managers.pop('NluManager')
			nodeRedManager = self._managers.pop('NodeRedManager')

			for manager in self._managers.values():
				if manager and manager.name != self.bugReportManager.name:
					manager.onStart()

			talkManager.onStart()
			nluManager.onStart()
			skillManager.onStart()
			deviceManager.onStart()
			widgetManager.onStart()
			dialogTemplateManager.onStart()
			assistantManager.onStart()
			nodeRedManager.onStart()

			self._managers[configManager.name] = configManager
			self._managers[audioServer.name] = audioServer
			self._managers[languageManager.name] = languageManager
			self._managers[locationManager.name] = locationManager
			self._managers[deviceManager.name] = deviceManager
			self._managers[talkManager.name] = talkManager
			self._managers[databaseManager.name] = databaseManager
			self._managers[userManager.name] = userManager
			self._managers[mqttManager.name] = mqttManager
			self._managers[webUINotificationManager.name] = webUINotificationManager
			self._managers[skillManager.name] = skillManager
			self._managers[widgetManager.name] = widgetManager
			self._managers[dialogTemplateManager.name] = dialogTemplateManager
			self._managers[assistantManager.name] = assistantManager
			self._managers[nluManager.name] = nluManager
			self._managers[internetManager.name] = internetManager
			self._managers[nodeRedManager.name] = nodeRedManager
			self._managers[stateManager.name] = stateManager
			self._managers[subprocessManager.name] = subprocessManager
			self._managers[bugReportManager.name] = bugReportManager
		except Exception as e:
			import traceback

			traceback.print_exc()
			Logger().logFatal(f'Error while starting managers: {e}')


	def onBooted(self):
		manager = None
		try:
			for manager in self._managers.values():
				if manager:
					manager.onBooted()
		except Exception as e:
			Logger().logError(f'Error while sending onBooted to manager **{manager.name}**: {e}')

		deviceList = self.deviceManager.getDevicesWithAbilities([DeviceAbility.IS_SATELITTE, DeviceAbility.IS_CORE], connectedOnly=False)
		self.mqttManager.playSound(soundFilename='boot', deviceUid=deviceList)


	@staticmethod
	def getInstance() -> SuperManager:
		return SuperManager._INSTANCE


	def initManagers(self):
		from core.commons.CommonsManager import CommonsManager
		from core.base.ConfigManager import ConfigManager
		from core.base.SkillManager import SkillManager
		from core.webui.WidgetManager import WidgetManager
		from core.device.DeviceManager import DeviceManager
		from core.myHome.LocationManager import LocationManager
		from core.dialog.MultiIntentManager import MultiIntentManager
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
		from core.webApi.ApiManager import ApiManager
		from core.webui.NodeRedManager import NodeRedManager
		from core.base.SkillStoreManager import SkillStoreManager
		from core.dialog.DialogTemplateManager import DialogTemplateManager
		from core.base.AssistantManager import AssistantManager
		from core.nlu.NluManager import NluManager
		from core.util.AliceWatchManager import AliceWatchManager
		from core.server.AudioServer import AudioManager
		from core.dialog.DialogManager import DialogManager
		from core.voice.WakewordManager import WakewordManager
		from core.webui.WebUIManager import WebUIManager
		from core.base.StateManager import StateManager
		from core.util.SubprocessManager import SubprocessManager
		from core.webui.WebUINotificationManager import WebUINotificationManager
		from core.util.BugReportManager import BugReportManager

		self.bugReportManager = BugReportManager()
		self.commonsManager = CommonsManager()
		self.commons = self.commonsManager
		self.stateManager = StateManager()
		self.subprocessManager = SubprocessManager()
		self.configManager = ConfigManager()
		self.databaseManager = DatabaseManager()
		self.skillManager = SkillManager()
		self.widgetManager = WidgetManager()
		self.deviceManager = DeviceManager()
		self.audioManager = AudioManager()
		self.languageManager = LanguageManager()
		self.asrManager = ASRManager()
		self.ttsManager = TTSManager()
		self.threadManager = ThreadManager()
		self.mqttManager = MqttManager()
		self.timeManager = TimeManager()
		self.userManager = UserManager()
		self.multiIntentManager = MultiIntentManager()
		self.telemetryManager = TelemetryManager()
		self.locationManager = LocationManager()
		self.internetManager = InternetManager()
		self.wakewordRecorder = WakewordRecorder()
		self.talkManager = TalkManager()
		self.webUiManager = WebUIManager()
		self.apiManager = ApiManager()
		self.nodeRedManager = NodeRedManager()
		self.skillStoreManager = SkillStoreManager()
		self.dialogTemplateManager = DialogTemplateManager()
		self.assistantManager = AssistantManager()
		self.nluManager = NluManager()
		self.aliceWatchManager = AliceWatchManager()
		self.dialogManager = DialogManager()
		self.wakewordManager = WakewordManager()
		self.webUINotificationManager = WebUINotificationManager()

		self._managers = {name[0].upper() + name[1:]: manager for name, manager in self.__dict__.items() if name.endswith('Manager')}


	def onStop(self):
		mqttManager = self._managers.pop('MqttManager', None) # Mqtt goes down last with bug reporter
		bugReportManager = self._managers.pop('BugReportManager', None) # bug reporter goes down as last

		skillManager = self._managers.pop('SkillManager', None) # Skill manager goes down first, to tell the skills
		if skillManager:
			try:
				skillManager.onStop()
			except Exception as e:
				Logger().logError(f'Error stopping SkillManager: {e}')

		for managerName, manager in self._managers.items():
			try:
				if manager.isActive:
					manager.onStop()
			except Exception as e:
				Logger().logError(f'Error while shutting down manager **{managerName}**: {e}')

		if mqttManager:
			try:
				mqttManager.onStop()
			except Exception as e:
				Logger().logError(f'Error stopping MqttManager: {e}')

		if bugReportManager:
			try:
				bugReportManager.onStop()
			except Exception as e:
				Logger().logError(f'Error stopping BugReportManager: {e}')


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
