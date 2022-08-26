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
		self.AliceWatchManager        = None #NOSONAR
		self.ApiManager               = None #NOSONAR
		self.ASRManager               = None #NOSONAR
		self.AssistantManager         = None #NOSONAR
		self.AudioManager             = None #NOSONAR
		self.BugReportManager         = None #NOSONAR
		self.Commons                  = None #NOSONAR
		self.CommonsManager           = None #NOSONAR
		self.ConfigManager            = None #NOSONAR
		self.DatabaseManager          = None #NOSONAR
		self.DeviceManager            = None #NOSONAR
		self.DialogManager            = None #NOSONAR
		self.DialogTemplateManager    = None #NOSONAR
		self.InternetManager          = None #NOSONAR
		self.LanguageManager          = None #NOSONAR
		self.LocationManager          = None #NOSONAR
		self.MqttManager              = None #NOSONAR
		self.MultiIntentManager       = None #NOSONAR
		self.NluManager               = None #NOSONAR
		self.NodeRedManager           = None #NOSONAR
		self.SkillManager             = None #NOSONAR
		self.SkillStoreManager        = None #NOSONAR
		self.StateManager             = None #NOSONAR
		self.SubprocessManager        = None #NOSONAR
		self.TalkManager              = None #NOSONAR
		self.TelemetryManager         = None #NOSONAR
		self.ThreadManager            = None #NOSONAR
		self.TimeManager              = None #NOSONAR
		self.TTSManager               = None #NOSONAR
		self.UserManager              = None #NOSONAR
		self.WakewordManager          = None #NOSONAR
		self.WakewordRecorder         = None #NOSONAR
		self.WebUiManager             = None #NOSONAR
		self.WebUINotificationManager = None #NOSONAR
		self.WidgetManager            = None #NOSONAR



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

			for manager in self._managers.copy().values():
				if manager and manager.name != self.BugReportManager.name:
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

		deviceList = self.DeviceManager.getDevicesWithAbilities([DeviceAbility.IS_SATELITTE, DeviceAbility.IS_CORE], connectedOnly=False)
		self.MqttManager.playSound(soundFilename='boot', deviceUid=deviceList)


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

		self.BugReportManager = BugReportManager()
		self.CommonsManager = CommonsManager()
		self.Commons = self.CommonsManager
		self.StateManager = StateManager()
		self.SubprocessManager = SubprocessManager()
		self.ConfigManager = ConfigManager()
		self.DatabaseManager = DatabaseManager()
		self.SkillManager = SkillManager()
		self.WidgetManager = WidgetManager()
		self.DeviceManager = DeviceManager()
		self.AudioManager = AudioManager()
		self.LanguageManager = LanguageManager()
		self.ASRManager = ASRManager()
		self.TTSManager = TTSManager()
		self.ThreadManager = ThreadManager()
		self.MqttManager = MqttManager()
		self.TimeManager = TimeManager()
		self.UserManager = UserManager()
		self.MultiIntentManager = MultiIntentManager()
		self.TelemetryManager = TelemetryManager()
		self.LocationManager = LocationManager()
		self.InternetManager = InternetManager()
		self.WakewordRecorder = WakewordRecorder()
		self.TalkManager = TalkManager()
		self.WebUiManager = WebUIManager()
		self.ApiManager = ApiManager()
		self.NodeRedManager = NodeRedManager()
		self.SkillStoreManager = SkillStoreManager()
		self.DialogTemplateManager = DialogTemplateManager()
		self.AssistantManager = AssistantManager()
		self.NluManager = NluManager()
		self.AliceWatchManager = AliceWatchManager()
		self.DialogManager = DialogManager()
		self.WakewordManager = WakewordManager()
		self.WebUINotificationManager = WebUINotificationManager()

		self._managers = {name: manager for name, manager in self.__dict__.items() if name.endswith('Manager')}


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
		managerInstance = self._managers.get(manager, None)
		if not managerInstance:
			Logger().logWarning(f'Was asking to restart manager **{manager}** but it doesn\'t exist')
			return

		managerInstance.onStop()
		managerInstance.onStart()
		managerInstance.onBooted()


	@property
	def managers(self) -> dict:
		return self._managers
