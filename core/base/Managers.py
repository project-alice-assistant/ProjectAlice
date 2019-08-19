# -*- coding: utf-8 -*-

import logging

from core.base.Manager import Manager

ConfigManager = None
ModuleManager = None
MqttServer = None
DeviceManager = None
ProtectedIntentManager = None
TalkManager = None
UserManager = None
DialogSessionManager = None
ThreadManager = None
TimeManager = None
MultiIntentManager = None
LanguageManager = None
ASRManager = None
SnipsServicesManager = None
SnipsConsoleManager = None
SamkillaManager = None
InternetManager = None
DatabaseManager = None
ProjectAlice = None
WakewordManager = None
TelemetryManager = None
TTSManager = None

_logger = logging.getLogger('ProjectAlice')
managers = dict()


def onStart():
	global managers
	managers = {
		'ProjectAlice'          : ProjectAlice,
		'ConfigManager'         : ConfigManager,
		'ModuleManager'         : ModuleManager,
		'MqttServer'            : MqttServer,
		'DeviceManager'         : DeviceManager,
		'ProtectedIntentManager': ProtectedIntentManager,
		'TalkManager'           : TalkManager,
		'UserManager'           : UserManager,
		'DialogSessionManager'  : DialogSessionManager,
		'ThreadManager'         : ThreadManager,
		'TimeManager'           : TimeManager,
		'MultiIntentManager'    : MultiIntentManager,
		'LanguageManager'       : LanguageManager,
		'ASRManager'            : ASRManager,
		'SnipsServicesManager'  : SnipsServicesManager,
		'SnipsConsoleManager'   : SnipsConsoleManager,
		'SamkillaManager'       : SamkillaManager,
		'InternetManager'       : InternetManager,
		'DatabaseManager'       : DatabaseManager,
		'WakewordManager'       : WakewordManager,
		'TelemetryManager'      : TelemetryManager,
		'TTSManager' 			: TTSManager
	}


def broadcast(method, exceptions: list = None, manager: Manager = None, args: list = None, propagateToModules: bool = False):
	global managers

	if not exceptions and not manager:
		_logger.warning("[Managers] Cannot broadcast to manager, the calling method has to be put in exceptions")

	if not args:
		args = list()

	if 'ProjectAlice' not in exceptions:
		exceptions.append('ProjectAlice')

	deadManagers = list()
	for name in managers.keys():
		man = managers[name]

		if not man:
			deadManagers.append(name)
			continue

		if (manager and man.name != manager.name) or man.name in exceptions:
			continue

		try:
			func = getattr(man, method)
			func(*args)
		except AttributeError:
			_logger.warning("[Managers] Couldn't find method {} in manager {}".format(method, man.name))

	if propagateToModules:
		managers['ModuleManager'].broadcast(method=method, args=args)

	for name in deadManagers:
		del managers[name]
