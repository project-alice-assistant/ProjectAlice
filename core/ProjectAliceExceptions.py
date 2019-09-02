import logging
import core.base.Managers as managers


class SamkillaException(Exception):

	def __init__(self, status: str, message: str, context: str):
		self._status = status
		self._message = message
		self._context = context
		super().__init__(message)


	@property
	def status(self) -> str:
		return self._status


	@property
	def message(self) -> str:
		return self._message


	@property
	def context(self) -> str:
		return self._context


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


class IntentError(SamkillaException):
	def __init__(self, status: str, message: str, context: str):
		super().__init__(status, message, context)


class HttpError(SamkillaException):
	def __init__(self, status: str, message: str, context: str):
		super().__init__(status, message, context)


class AssistantNotFoundError(SamkillaException):
	def __init__(self, status: str, message: str, context: str):
		super().__init__(status, message, context)


class LanguageManagerLangNotSupported(Exception): pass
class ConfigurationUpdateFailed(Exception): pass
class ModuleNotConditionCompliant(Exception): pass
class AccessLevelTooLow(Exception): pass
