import logging
import core.base.Managers as managers


class LanguageManagerLangNotSupported(Exception): pass
class ConfigurationUpdateFailed(Exception): pass

class FunctionNotImplemented(Exception):
	def __init__(self, clazz: str, funcName: str):
		raise NotImplementedError('[{}] {} needs implementation!!'.format(clazz, funcName))

class ModuleStartingFailed(Exception):
	def __init__(self, moduleName: str = '', error: str = ''):
		self._logger = logging.getLogger('ProjectAlice')
		self._logger.error('An error occured while starting a module: {}'.format(error))

		if moduleName:
			managers.ConfigManager.deactivateModule(moduleName)
			managers.ModuleManager.deactivateModule(moduleName)

class ModuleStartDelayed(Exception):
	def __init__(self, moduleName):
		self._logger = logging.getLogger('ProjectAlice')
		self._logger.warning('[{}] Delaying module start'.format(moduleName))
		managers.ModuleManager.getModuleInstance(moduleName).delayed = True


class ModuleNotConditionCompliant(Exception): pass

class AccessLevelTooLow(Exception): pass
