import json

import core.base.SuperManager as SM
from core.commons import constants
from core.util.model.Logger import Logger


class ProjectAliceObject(Logger):

	def __init__(self, logDepth: int = 3, *args, **kwargs):
		self._depth = logDepth
		super().__init__(depth=self._depth)


	def __repr__(self):
		return json.dumps(self.__dict__)


	def __str__(self):
		return json.dumps(self.__dict__)


	def broadcast(self, method: str, exceptions: list = None, manager = None, propagateToSkills: bool = False, *args, **kwargs):
		if not exceptions:
			exceptions = list()

		if isinstance(exceptions, str):
			exceptions = [exceptions]

		if not exceptions and not manager:
			# Prevent infinite loop of broadcaster being broadcasted to re broadcasting
			self.logWarning('Cannot broadcast to itself, the calling method has to be put in exceptions')
			return

		if 'ProjectAlice' not in exceptions:
			exceptions.append('ProjectAlice')

		deadManagers = list()
		for name, man in SM.SuperManager.getInstance().managers.items():
			if not man:
				deadManagers.append(name)
				continue

			if (manager and man.name != manager.name) or man.name in exceptions:
				continue

			try:
				func = getattr(skillItem, method, None)
				if func:
					func(*args, **kwargs)
			except TypeError:
				# Do nothing, it's most prolly kwargs
				pass

		if propagateToSkills:
			self.SkillManager.skillBroadcast(method=method, *args, **kwargs)

		for name in deadManagers:
			del SM.SuperManager.getInstance().managers[name]


	@property
	def ProjectAlice(self):
		return SM.SuperManager.getInstance().projectAlice


	@property
	def ConfigManager(self):
		return SM.SuperManager.getInstance().configManager


	@property
	def SkillManager(self):
		return SM.SuperManager.getInstance().skillManager


	@property
	def DeviceManager(self):
		return SM.SuperManager.getInstance().deviceManager


	@property
	def DialogSessionManager(self):
		return SM.SuperManager.getInstance().dialogSessionManager


	@property
	def MultiIntentManager(self):
		return SM.SuperManager.getInstance().multiIntentManager


	@property
	def ProtectedIntentManager(self):
		return SM.SuperManager.getInstance().protectedIntentManager


	@property
	def MqttManager(self):
		return SM.SuperManager.getInstance().mqttManager


	@property
	def SamkillaManager(self):
		return SM.SuperManager.getInstance().samkillaManager


	@property
	def SnipsConsoleManager(self):
		return SM.SuperManager.getInstance().snipsConsoleManager


	@property
	def SnipsServicesManager(self):
		return SM.SuperManager.getInstance().snipsServicesManager


	@property
	def UserManager(self):
		return SM.SuperManager.getInstance().userManager


	@property
	def DatabaseManager(self):
		return SM.SuperManager.getInstance().databaseManager


	@property
	def InternetManager(self):
		return SM.SuperManager.getInstance().internetManager


	@property
	def TelemetryManager(self):
		return SM.SuperManager.getInstance().telemetryManager


	@property
	def ThreadManager(self):
		return SM.SuperManager.getInstance().threadManager


	@property
	def TimeManager(self):
		return SM.SuperManager.getInstance().timeManager


	@property
	def ASRManager(self):
		return SM.SuperManager.getInstance().asrManager


	@property
	def LanguageManager(self):
		return SM.SuperManager.getInstance().languageManager


	@property
	def TalkManager(self):
		return SM.SuperManager.getInstance().talkManager


	@property
	def TTSManager(self):
		return SM.SuperManager.getInstance().ttsManager


	@property
	def WakewordManager(self):
		return SM.SuperManager.getInstance().wakewordManager


	@property
	def WebInterfaceManager(self):
		return SM.SuperManager.getInstance().webInterfaceManager


	@property
	def Commons(self):
		return SM.SuperManager.getInstance().commonsManager


	@property
	def SnipsWatchManager(self):
		return SM.SuperManager.getInstance().snipsWatchManager
