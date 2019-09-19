import logging

from core.base.SuperManager import SuperManager


class SamkillaException(Exception):

	def __init__(self, status: int, message: str, context: list):
		self._status = status
		self._message = message
		self._context = context
		super().__init__(message)


	@property
	def status(self) -> int:
		return self._status


	@property
	def message(self) -> str:
		return self._message


	@property
	def context(self) -> list:
		return self._context


class FunctionNotImplemented(Exception):
	def __init__(self, clazz: str, funcName: str):
		raise NotImplementedError('[{}] {} needs implementation!!'.format(clazz, funcName))


class ModuleStartingFailed(Exception):
	def __init__(self, moduleName: str = '', error: str = ''):
		self._logger = logging.getLogger('ProjectAlice')
		self._logger.error('An error occured while starting a module: {}'.format(error))

		if moduleName:
			SuperManager.getInstance().configManager.deactivateModule(moduleName)
			SuperManager.getInstance().moduleManager.deactivateModule(moduleName)


class ModuleStartDelayed(Exception):
	def __init__(self, moduleName):
		self._logger = logging.getLogger('ProjectAlice')
		self._logger.warning('[{}] Delaying module start'.format(moduleName))
		SuperManager.getInstance().moduleManager.getModuleInstance(moduleName).delayed = True


class IntentError(SamkillaException):
	def __init__(self, status: int, message: str, context: list):
		super().__init__(status, message, context)


class HttpError(SamkillaException):
	def __init__(self, status: int, message: str, context: list):
		super().__init__(status, message, context)


class AssistantNotFoundError(SamkillaException):
	def __init__(self, status: int, message: str, context: list):
		super().__init__(status, message, context)


class ModuleNotConditionCompliant(Exception):

	def __init__(self, message: str, moduleName: str, condition: str, conditionValue: str):
		self._moduleName = moduleName
		self._condition = condition
		self._conditionValue = conditionValue
		super().__init__(message)


	@property
	def moduleName(self) -> str:
		return self._moduleName


	@property
	def condition(self) -> str:
		return self._condition


	@property
	def conditionValue(self) -> str:
		return self._conditionValue


class AccessLevelTooLow(Exception): pass
class GithubTokenFailed(Exception): pass
class GithubRateLimit(Exception): pass
class LanguageManagerLangNotSupported(Exception): pass
class ConfigurationUpdateFailed(Exception): pass
