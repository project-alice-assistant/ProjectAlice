#  Copyright (c) 2021
#
#  This file, ProjectAliceExceptions.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:47 CEST

import typing

from core.base.SuperManager import SuperManager
from core.util.model.Logger import Logger


class ProjectAliceException(Exception):

	def __init__(self, message: str = None, status: int = None, context: list = None):
		self._logger = Logger()
		self._message = message
		self._status = status
		self._context = context
		super().__init__(message)


	@property
	def message(self) -> str:
		return self._message


	@property
	def status(self) -> typing.Optional[int]:
		return self._status


	@property
	def context(self) -> typing.Optional[list]:
		return self._context


class FunctionNotImplemented(ProjectAliceException):

	def __init__(self, clazz: str, funcName: str):
		self._logger.logError(f'{funcName} must be implemented in {clazz}!')


class SkillStartingFailed(ProjectAliceException):

	def __init__(self, skillName: str, error: str = ''):
		super().__init__(message=error)
		self._logger.logWarning(f'[{skillName}] Error starting skill: {error}')

		if skillName in SuperManager.getInstance().SkillManager.NEEDED_SKILLS:
			self._logger.logFatal(f'Skill **{skillName}** is required to continue, sorry')
		else:
			SuperManager.getInstance().SkillManager.deactivateSkill(skillName)


class SkillInstanceFailed(ProjectAliceException):

	def __init__(self, skillName: str, error: str = ''):
		super().__init__(message=error)
		self._logger.logWarning(f'[{skillName}] Error creating skill instance: {error}')

		if skillName in SuperManager.getInstance().SkillManager.NEEDED_SKILLS:
			self._logger.logFatal(f'Skill **{skillName}** is required to continue, sorry')
		else:
			SuperManager.getInstance().SkillManager.deactivateSkill(skillName)


class SkillStartDelayed(ProjectAliceException):

	def __init__(self, skillName):
		super().__init__(skillName)
		self._logger.logWarning(f'[{skillName}] Delaying skill start')
		SuperManager.getInstance().SkillManager.getSkillInstance(skillName).delayed = True


class IntentError(ProjectAliceException):

	def __init__(self, status: int, message: str, context: list):
		super().__init__(message, status, context)


class HttpError(ProjectAliceException):

	def __init__(self, status: int, message: str, context: list):
		super().__init__(message, status, context)


class IntentWithUnknownSlotError(ProjectAliceException):

	def __init__(self, status: int, message: str, context: list):
		super().__init__(message, status, context)


class AssistantNotFoundError(ProjectAliceException):

	def __init__(self, status: int, message: str, context: list):
		super().__init__(message, status, context)


class SkillNotConditionCompliant(ProjectAliceException):

	def __init__(self, message: str, skillName: str, condition: str, conditionValue: str):
		self._skillName = skillName
		self._condition = condition
		self._conditionValue = conditionValue
		super().__init__(message)


	@property
	def skillName(self) -> str:
		return self._skillName


	@property
	def condition(self) -> str:
		return self._condition


	@property
	def conditionValue(self) -> str:
		return self._conditionValue


class OfflineError(ProjectAliceException):
	pass  # Raised for capture only


class DbConnectionError(ProjectAliceException):
	pass  # Raised for capture only


class InvalidQuery(ProjectAliceException):
	pass  # Raised for capture only


class AccessLevelTooLow(ProjectAliceException):
	pass  # Raised for capture only


class GithubTokenFailed(ProjectAliceException):
	pass  # Raised for capture only


class GithubRateLimit(ProjectAliceException):
	pass  # Raised for capture only


class GithubNotFound(ProjectAliceException):
	pass  # Raised for capture only


class LanguageManagerLangNotSupported(ProjectAliceException):
	pass  # Raised for capture only


class ConfigurationUpdateFailed(ProjectAliceException):
	pass  # Raised for capture only


class PlayBytesStopped(ProjectAliceException):
	pass  # Raised for capture only


class PlayBytesFinished(ProjectAliceException):
	pass  # Ra

class TTSFinished(ProjectAliceException):
	pass  # Raised for capture only


class VitalConfigMissing(ProjectAliceException):

	def __init__(self, message: str = None):
		super().__init__(message)
		self._logger.logWarning(f'A vital configuration --{message}-- is missing. Make sure the following configurations are set: {" / ".join(SuperManager.getInstance().ConfigManager.vitalConfigs)}')
		SuperManager.getInstance().projectAlice.onStop()


class StateAlreadyRegistered(ProjectAliceException):

	def __init__(self, message: str = None):
		super().__init__()
		self._logger.logWarning(message)
