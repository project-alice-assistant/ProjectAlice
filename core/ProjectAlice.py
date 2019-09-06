import subprocess
import os
from pathlib import Path

import django
from django.core import management

import core.base.Managers as Managers
from core.base.ConfigManager import ConfigManager
from core.base.ModuleManager import ModuleManager
from core.commons import commons
from core.commons.model.Singleton import Singleton
from core.device.DeviceManager import DeviceManager
from core.dialog.DialogSessionManager import DialogSessionManager
from core.dialog.MultiIntentManager import MultiIntentManager
from core.dialog.ProtectedIntentManager import ProtectedIntentManager
from core.server.MqttServer import MqttServer
from core.snips.SamkillaManager import SamkillaManager
from core.snips.SnipsConsoleManager import SnipsConsoleManager
from core.snips.SnipsServicesManager import SnipsServicesManager
from core.user.UserManager import UserManager
from core.util.DatabaseManager import DatabaseManager
from core.util.InternetManager import InternetManager
from core.util.TelemetryManager import TelemetryManager
from core.util.ThreadManager import ThreadManager
from core.util.TimeManager import TimeManager
from core.voice.ASRManager import ASRManager
from core.voice.LanguageManager import LanguageManager
from core.voice.TalkManager import TalkManager
from core.voice.TTSManager import TTSManager
from core.voice.WakewordManager import WakewordManager


class ProjectAlice(Singleton):

	NAME = 'ProjectAlice'

	def __init__(self):
		Singleton.__init__(self, self.NAME)
		self._logger.info('Starting up project Alice core')
		Managers.ProjectAlice 					= self

		self._configManager 					= ConfigManager(self)
		self._configManager.onStart()

		self._databaseManager 					= DatabaseManager(self)
		self._databaseManager.onStart()

		self._languageManager					= LanguageManager(self)
		self._languageManager.onStart()

		subprocess.run(['ln', '-sfn', Path(commons.rootDir(),'trained/assistants/assistant_{}'.format(self._languageManager.activeLanguage)), Path(commons.rootDir(), 'assistant')])

		self._snipsServicesManager 				= SnipsServicesManager(self)
		self._snipsServicesManager.onStart()
		self._ASRManager 						= ASRManager(self)
		self._TTSManager 						= TTSManager(self)

		self._threadsManager 					= ThreadManager(self)
		self._protectedIntentsManager 			= ProtectedIntentManager(self)
		self._mqttServer 						= MqttServer(self)
		self._timeManager 						= TimeManager(self)

		self._usersManager 						= UserManager(self)
		self._snipsSessionManager 				= DialogSessionManager(self)
		self._multiIntentManager 				= MultiIntentManager(self)
		self._telemetryManager                  = TelemetryManager(self)
		self._moduleManager                     = ModuleManager(self)
		self._devicesManager 					= DeviceManager(self)
		self._internetManager 					= InternetManager(self)
		self._snipsConsoleManager 				= SnipsConsoleManager(self)
		self._samkillaManager	 				= SamkillaManager(self)
		self._wakewordManager 					= WakewordManager(self)

		self._randomTalkManager 				= TalkManager(self)

		Managers.onStart()

		self._randomTalkManager.onStart()
		self._languageManager.loadStrings()

		self._threadsManager.onStart()
		self._internetManager.onStart()
		self._ASRManager.onStart()
		self._TTSManager.onStart()
		self._protectedIntentsManager.onStart()
		self._timeManager.onStart()
		self._usersManager.onStart()
		self._mqttServer.onStart()
		self._snipsSessionManager.onStart()
		self._multiIntentManager.onStart()
		self._devicesManager.onStart()
		self._wakewordManager.onStart()
		self._telemetryManager.onStart()
		self._moduleManager.onStart()

		if self._internetManager.online:
			self._snipsConsoleManager.onStart()
			self._samkillaManager.onStart()

		if self._configManager.getAliceConfigByName('webInterfaceActive'):
			self._threadsManager.newThread(name='Django', target=self._startDjango)

		if self._configManager.getAliceConfigByName('useSLC'):
			subprocess.run(['sudo', 'systemctl', 'start', 'snipsledcontrol'])

		Managers.MqttServer.playSound(soundFile='boot')

		Managers.broadcast(method='onBooted', exceptions=['dummy'])


	@property
	def name(self) -> str:
		return self.NAME

	def onStop(self):
		self._logger.info('[ProjectAlice] Shutting down Project Alice')
		try:
			self._moduleManager.onStop()
			self._devicesManager.onStop()
			self._mqttServer.onStop()
			self._randomTalkManager.onStop()
			self._protectedIntentsManager.onStop()
			self._configManager.onStop()
			self._usersManager.onStop()
			self._snipsSessionManager.onStop()
			self._multiIntentManager.onStop()
			self._timeManager.onStop()
			self._threadsManager.onStop()
			self._internetManager.onStop()
			self._snipsConsoleManager.onStop()
			self._samkillaManager.onStop()
			self._wakewordManager.onStop()
			self._telemetryManager.onStop()

			if self._configManager.getAliceConfigByName('useSLC'):
				subprocess.run(['sudo', 'systemctl', 'stop', 'snipsledcontrol'])

			self._snipsServicesManager.onStop()
			self._databaseManager.onStop()
		except Exception as e:
			self._logger.info('[ProjectAlice] Error while shutting down Project Alice: {}'.format(e))


	@staticmethod
	def _startDjango():
		os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.gui.settings')
		django.setup()
		management.call_command('runserver', '0:8000', '--noreload')
