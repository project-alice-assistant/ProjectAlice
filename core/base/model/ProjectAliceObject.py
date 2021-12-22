#  Copyright (c) 2021
#
#  This file, ProjectAliceObject.py, is part of Project Alice.
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

import json
import re
from copy import copy
from importlib_metadata import PackageNotFoundError, version as packageVersion
from pathlib import Path
from typing import TYPE_CHECKING, Union

import core.base.SuperManager as SM
from core.base.model.Version import Version
from core.commons import constants
from core.util.model.Logger import Logger


if TYPE_CHECKING:
	from core.device.DeviceManager import DeviceManager
	from core.ProjectAlice import ProjectAlice
	from core.asr.ASRManager import ASRManager
	from core.base.AssistantManager import AssistantManager
	from core.base.ConfigManager import ConfigManager
	from core.base.SkillStoreManager import SkillStoreManager
	from core.base.StateManager import StateManager
	from core.commons.CommonsManager import CommonsManager
	from core.myHome.LocationManager import LocationManager
	from core.dialog.DialogManager import DialogManager
	from core.dialog.DialogTemplateManager import DialogTemplateManager
	from core.dialog.MultiIntentManager import MultiIntentManager
	from core.nlu.NluManager import NluManager
	from core.server.AudioServer import AudioManager
	from core.server.MqttManager import MqttManager
	from core.user.UserManager import UserManager
	from core.util.AliceWatchManager import AliceWatchManager
	from core.util.DatabaseManager import DatabaseManager
	from core.util.InternetManager import InternetManager
	from core.util.TelemetryManager import TelemetryManager
	from core.util.ThreadManager import ThreadManager
	from core.util.TimeManager import TimeManager
	from core.util.BugReportManager import BugReportManager
	from core.util.SubprocessManager import SubprocessManager
	from core.voice.LanguageManager import LanguageManager
	from core.voice.TTSManager import TTSManager
	from core.voice.TalkManager import TalkManager
	from core.voice.WakewordManager import WakewordManager
	from core.voice.WakewordRecorder import WakewordRecorder
	from core.webApi.ApiManager import ApiManager
	from core.webui.NodeRedManager import NodeRedManager
	from core.webui.WidgetManager import WidgetManager
	from core.webui.WebUINotificationManager import WebUINotificationManager


class ProjectAliceObject(object):
	DEPENDENCIES = {
		'internal': {},
		'external': {},
		'system'  : [],
		'pip'     : []
	}


	def __init__(self, *args, **kwargs):
		self._logger = Logger(*args, **kwargs)


	def __repr__(self) -> str:
		ret = copy(self.__dict__)
		ret.pop('_logger')
		return json.dumps(ret)


	def __str__(self) -> str:
		return self.__repr__()


	def broadcast(self, method: str, exceptions: list = None, manager=None, propagateToSkills: bool = False, **kwargs):  # NOSONAR
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

		if 'DialogManager' not in exceptions:
			exceptions.append('DialogManager')

		if not method.startswith('on'):
			method = f'on{method[0].capitalize() + method[1:]}'

		# Give absolute priority to DialogManager
		try:
			func = getattr(SM.SuperManager.getInstance().getManager('DialogManager'), method, None)
			if func:
				func(**kwargs)

		except TypeError as e:
			self.logWarning(f'Failed to broadcast event **{method}** to **DialogManager**: {e}')

		deadManagers = list()
		for name, man in SM.SuperManager.getInstance().managers.copy().items():
			if not man:
				deadManagers.append(name)
				continue

			if (manager and man.name != manager.name) or man.name in exceptions:
				continue

			try:
				func = getattr(man, method, None)
				if func:
					func(**kwargs)

			except TypeError as e:
				self.logWarning(f'Failed to broadcast event **{method}** to **{man.name}**: {e}')

		if propagateToSkills:
			self.SkillManager.skillBroadcast(method=method, **kwargs)

		for name in deadManagers:
			del SM.SuperManager.getInstance().managers[name]

		if method == 'onAudioFrame':
			return

		# Now send the event over mqtt
		payload = dict()
		for item, value in kwargs.items():
			try:
				payload[item] = json.dumps(value)
			except:
				# Cannot serialize that attribute, do nothing
				pass

		self.MqttManager.publish(
			topic=f'projectalice/events/{method}',
			payload=payload
		)


	def checkDependencies(self) -> bool:
		self.logInfo('Checking dependencies')

		for dep in {**self.DEPENDENCIES.get('internal', dict()), **self.DEPENDENCIES.get('external', dict())}:
			result = self.Commons.runRootSystemCommand(['dpkg-query', '-l', dep])
			if result.returncode:
				self.logWarning(f'Found missing dependency: {dep}')
				return False

		for dep in self.DEPENDENCIES['pip']:
			match = re.match(r'^([a-zA-Z0-9-_]*)(?:([=><]{0,2})([\d.]*)$)', dep)
			if not match:
				continue

			packageName, operator, version = match.groups()
			if not packageName:
				self.logWarning('Wrongly declared PIP requirement')
				continue

			try:
				installedVersion = packageVersion(packageName)
			except PackageNotFoundError:
				self.logWarning(f'Found missing dependencies: {packageName}')
				return False

			if not installedVersion or not operator or not version:
				continue

			version = Version.fromString(version)
			installedVersion = Version.fromString(installedVersion)

			if (operator == '==' and version != installedVersion) or \
					(operator == '>=' and installedVersion < version) or \
					(operator == '>' and (installedVersion < version or installedVersion == version)) or \
					(operator == '<' and (installedVersion > version or installedVersion == version)):

				self.logWarning(f'Dependency "{packageName}" is not conform with version requirements')
				return False

		for dep in self.DEPENDENCIES['system']:
			result = self.Commons.runRootSystemCommand(['dpkg-query', '-l', dep])
			if result.returncode:
				self.logWarning(f'Found missing dependency: {dep}')
				return False

		return True


	def installDependencies(self) -> bool:
		self.logInfo('Installing dependencies')

		try:
			for dep, link in self.DEPENDENCIES.get('internal', dict()).items():
				self.logInfo(f'Installing "{dep}"')
				result = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', f'./{link}'])
				if result.returncode:
					raise Exception(result.stderr)

				self.logInfo(f'Installed!')

			for dep, link in self.DEPENDENCIES.get('external', dict()).items():
				self.logInfo(f'Downloading "{dep}"')
				if not self.Commons.downloadFile(link, link.rsplit('/')[-1]):
					return False

				self.logInfo(f'Installing "{dep}"')
				result = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', f'./{link.rsplit("/")[-1]}'])
				if result.returncode:
					raise Exception(result.stderr)

				Path(link.rsplit('/')[-1]).unlink()

				self.logInfo(f'Installed!')

			for dep in self.DEPENDENCIES['system']:
				self.logInfo(f'Installing "{dep}"')
				result = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', dep])
				if result.returncode:
					raise Exception(result.stderr)

				self.logInfo(f'Installed!')

			for dep in self.DEPENDENCIES['pip']:
				self.logInfo(f'Installing "{dep}"')
				result = self.Commons.runSystemCommand(['./venv/bin/pip', 'install', dep])
				if result.returncode:
					raise Exception(result.stderr)

				self.logInfo(f'Installed!')

			return True
		except Exception as e:
			self.logError(f'Installing dependencies failed: {e}')
			return False


	def logInfo(self, msg: str, plural: Union[list, str] = None):
		self._logger.doLog(function='info', msg=self.decorateLogs(msg), printStack=False, plural=plural)


	def logError(self, msg: str, plural: Union[list, str] = None):
		self._logger.doLog(function='error', msg=self.decorateLogs(msg), plural=plural)


	def logDebug(self, msg: str, plural: Union[list, str] = None):
		self._logger.doLog(function='debug', msg=self.decorateLogs(msg), printStack=False, plural=plural)


	def logFatal(self, msg: str, plural: Union[list, str] = None):
		self._logger.doLog(function='fatal', msg=self.decorateLogs(msg), plural=plural)
		try:
			self.ProjectAlice.onStop()
		except:
			exit()


	def logWarning(self, msg: str, printStack: bool = False, plural: Union[list, str] = None):
		self._logger.doLog(function='warning', msg=self.decorateLogs(msg), printStack=printStack, plural=plural)


	def logCritical(self, msg: str, plural: Union[list, str] = None):
		self._logger.doLog(function='critical', msg=self.decorateLogs(msg), plural=plural)


	def decorateLogs(self, text: str) -> str:
		return f'[{self.__class__.__name__}] {text}'


	def onStart(self):
		pass  # Super object function is overridden only if needed


	def onStop(self, **kwargs):
		pass  # Super object function is overridden only if needed


	def onBooted(self):
		pass  # Super object function is overridden only if needed


	def onSkillInstalled(self, skill: str):
		pass  # Super object function is overridden only if needed


	def onSkillDeleted(self, skill: str):
		pass  # Super object function is overridden only if needed


	def onSkillUpdated(self, skill: str):
		pass  # Super object function is overridden only if needed


	def onSkillUpdating(self, skill: str):
		pass  # Super object function is overridden only if needed


	def onSkillStarted(self, skill: str):
		pass  # Super object function is overridden only if needed


	def onSkillStopped(self, skill: str):
		pass  # Super object function is overridden only if needed


	def onSkillActivated(self, skill: str):
		pass  # Super object function is overridden only if needed


	def onSkillDeactivated(self, skill: str):
		pass  # Super object function is overridden only if needed


	def onInternetConnected(self):
		pass  # Super object function is overridden only if needed


	def onInternetLost(self):
		pass  # Super object function is overridden only if needed


	def onHotword(self, deviceUid: str, user: str = constants.UNKNOWN_USER):
		pass  # Super object function is overridden only if needed


	def onHotwordToggleOn(self, deviceUid: str, session):
		pass  # Super object function is overridden only if needed


	def onHotwordToggleOff(self, deviceUid: str, session):
		pass  # Super object function is overridden only if needed


	def onSessionStarted(self, session):
		pass  # Super object function is overridden only if needed


	def onContinueSession(self, session):
		pass  # Super object function is overridden only if needed


	def onAsrToggleOn(self, deviceUid: str):
		pass  # Super object function is overridden only if needed


	def onAsrToggleOff(self, deviceUid: str):
		pass  # Super object function is overridden only if needed


	def onStartListening(self, session):
		pass  # Super object function is overridden only if needed


	def onStopListening(self, session):
		pass  # Super object function is overridden only if needed


	def onCaptured(self, session):
		pass  # Super object function is overridden only if needed


	def onNluQuery(self, session):
		pass  # Super object function is overridden only if needed


	def onIntentParsed(self, session):
		pass  # Super object function is overridden only if needed


	def onIntent(self, session):
		pass  # Super object function is overridden only if needed


	def onConfigureIntent(self, intents: list):
		pass  # Super object function is overridden only if needed


	def onUserCancel(self, session):
		pass  # Super object function is overridden only if needed


	def onSessionTimeout(self, session):
		pass  # Super object function is overridden only if needed


	def onIntentNotRecognized(self, session):
		pass  # Super object function is overridden only if needed


	def onNluIntentNotRecognized(self, session):
		pass  # Super object function is overridden only if needed


	def onNluError(self, session):
		pass  # Super object function is overridden only if needed


	def onSessionError(self, session):
		pass  # Super object function is overridden only if needed


	def onStartSession(self, deviceUid: str, payload: dict):
		pass  # Super object function is overridden only if needed


	def onSessionEnded(self, session):
		pass  # Super object function is overridden only if needed


	def onSay(self, session):
		pass  # Super object function is overridden only if needed


	def onSayFinished(self, session, uid: str = None):
		pass  # Super object function is overridden only if needed


	def onSessionQueued(self, session):
		pass  # Super object function is overridden only if needed


	def onMessage(self, session) -> bool:  # NOSONAR
		""" Do not consume the intent by default """
		return False


	def onSleep(self):
		pass  # Super object function is overridden only if needed


	def onWakeup(self):
		pass  # Super object function is overridden only if needed


	def onGoingBed(self):
		pass  # Super object function is overridden only if needed


	def onLeavingHome(self):
		pass  # Super object function is overridden only if needed


	def onReturningHome(self):
		pass  # Super object function is overridden only if needed


	def onEating(self):
		pass  # Super object function is overridden only if needed


	def onWatchingTV(self):
		pass  # Super object function is overridden only if needed


	def onCooking(self):
		pass  # Super object function is overridden only if needed


	def onMakeup(self):
		pass  # Super object function is overridden only if needed


	def onContextSensitiveDelete(self, session):
		pass  # Super object function is overridden only if needed


	def onContextSensitiveEdit(self, session):
		pass  # Super object function is overridden only if needed


	def onFullMinute(self):
		pass  # Super object function is overridden only if needed


	def onFiveMinute(self):
		pass  # Super object function is overridden only if needed


	def onQuarterHour(self):
		pass  # Super object function is overridden only if needed


	def onFullHour(self):
		pass  # Super object function is overridden only if needed


	def onWakeword(self, deviceUid: str, user: str = constants.UNKNOWN_USER):
		pass  # Super object function is overridden only if needed


	def onMotionDetected(self):
		pass  # Super object function is overridden only if needed


	def onMotionStopped(self):
		pass  # Super object function is overridden only if needed


	def onButtonPressed(self):
		pass  # Super object function is overridden only if needed


	def onButtonReleased(self):
		pass  # Super object function is overridden only if needed


	def onDeviceDiscovered(self, device, uid: str):
		pass  # Super object function is overridden only if needed


	def onDeviceAdded(self, device, uid: str):
		pass  # Super object function is overridden only if needed


	def onDeviceRemoved(self, device, uid: str):
		pass  # Super object function is overridden only if needed


	def onDeviceConnecting(self):
		pass  # Super object function is overridden only if needed


	def onDeviceDisconnecting(self):
		pass  # Super object function is overridden only if needed


	def onUVIndexAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onRaining(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onTooMuchRain(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onWindy(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onFreezing(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onTemperatureHighAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onTemperatureLowAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onCOTwoAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onHumidityHighAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onHumidityLowAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onNoiseAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onPressureHighAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onGasAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onPressureLowAlert(self, *args, **kwargs):
		pass  # Super object function is overridden only if needed


	def onBroadcastingForNewDeviceStart(self):
		pass  # Super object function is overridden only if needed


	def onBroadcastingForNewDeviceStop(self, *args):
		pass  # Super object function is overridden only if needed


	def onAuthenticated(self, session):
		pass  # Super object function is overridden only if needed


	def onAuthenticationFailed(self, session):
		pass  # Super object function is overridden only if needed


	def onAudioFrame(self, **kwargs):
		pass  # Super object function is overridden only if needed


	def onAssistantInstalled(self, **kwargs):
		pass  # Super object function is overridden only if needed


	def onAssistantFailedTraining(self, **kwargs):
		pass  # Super object function is overridden only if needed


	def onSkillInstallFailed(self, skill: str):
		pass  # Super object function is overridden only if needed


	def onNluTrained(self, **kwargs):
		pass  # Super object function is overridden only if needed


	def onVadUp(self, **kwargs):
		pass  # Super object function is overridden only if needed


	def onVadDown(self, **kwargs):
		pass  # Super object function is overridden only if needed


	def onPlayBytes(self, payload: bytearray, deviceUid: str, sessionId: str = None):
		pass  # Super object function is overridden only if needed


	def onPlayBytesFinished(self, deviceUid: str, sessionId: str = None):
		pass  # Super object function is overridden only if needed


	def onToggleFeedbackOn(self, deviceUid: str):
		pass  # Super object function is overridden only if needed


	def onToggleFeedbackOff(self, deviceUid: str):
		pass  # Super object function is overridden only if needed


	def onPartialTextCaptured(self, session, text: str, likelihood: float, seconds: float):
		pass  # Super object function is overridden only if needed


	def onEndSession(self, session, reason: str = 'nominal'):
		pass  # Super object function is overridden only if needed


	def onDeviceHeartbeat(self, uid: str, deviceUid: str = None):
		pass  # Super object function is overridden only if needed


	def onDeviceStatus(self, session):
		pass  # Super object function is overridden only if needed


	@property
	def ProjectAlice(self) -> ProjectAlice:  # NOSONAR
		return SM.SuperManager.getInstance().projectAlice


	@property
	def ConfigManager(self) -> ConfigManager:  # NOSONAR
		return SM.SuperManager.getInstance().ConfigManager


	@property
	def SkillManager(self) -> SkillManager:  # NOSONAR
		return SM.SuperManager.getInstance().SkillManager


	@property
	def DeviceManager(self) -> DeviceManager:  # NOSONAR
		return SM.SuperManager.getInstance().DeviceManager


	@property
	def MultiIntentManager(self) -> MultiIntentManager:  # NOSONAR
		return SM.SuperManager.getInstance().MultiIntentManager


	@property
	def MqttManager(self) -> MqttManager:  # NOSONAR
		return SM.SuperManager.getInstance().MqttManager


	@property
	def UserManager(self) -> UserManager:  # NOSONAR
		return SM.SuperManager.getInstance().UserManager


	@property
	def DatabaseManager(self) -> DatabaseManager:  # NOSONAR
		return SM.SuperManager.getInstance().DatabaseManager


	@property
	def InternetManager(self) -> InternetManager:  # NOSONAR
		return SM.SuperManager.getInstance().InternetManager


	@property
	def TelemetryManager(self) -> TelemetryManager:  # NOSONAR
		return SM.SuperManager.getInstance().TelemetryManager


	@property
	def ThreadManager(self) -> ThreadManager:  # NOSONAR
		return SM.SuperManager.getInstance().ThreadManager


	@property
	def TimeManager(self) -> TimeManager:  # NOSONAR
		return SM.SuperManager.getInstance().TimeManager


	@property
	def ASRManager(self) -> ASRManager:  # NOSONAR
		return SM.SuperManager.getInstance().ASRManager


	@property
	def LanguageManager(self) -> LanguageManager:  # NOSONAR
		return SM.SuperManager.getInstance().LanguageManager


	@property
	def TalkManager(self) -> TalkManager:  # NOSONAR
		return SM.SuperManager.getInstance().TalkManager


	@property
	def TTSManager(self) -> TTSManager:  # NOSONAR
		return SM.SuperManager.getInstance().TTSManager


	@property
	def WakewordRecorder(self) -> WakewordRecorder:  # NOSONAR
		return SM.SuperManager.getInstance().WakewordRecorder


	@property
	def ApiManager(self) -> ApiManager:  # NOSONAR
		return SM.SuperManager.getInstance().ApiManager


	@property
	def Commons(self) -> CommonsManager:  # NOSONAR
		return SM.SuperManager.getInstance().CommonsManager


	@property
	def SkillStoreManager(self) -> SkillStoreManager:  # NOSONAR
		return SM.SuperManager.getInstance().SkillStoreManager


	@property
	def NluManager(self) -> NluManager:  # NOSONAR
		return SM.SuperManager.getInstance().NluManager


	@property
	def DialogTemplateManager(self) -> DialogTemplateManager:  # NOSONAR
		return SM.SuperManager.getInstance().DialogTemplateManager


	@property
	def AssistantManager(self) -> AssistantManager:  # NOSONAR
		return SM.SuperManager.getInstance().AssistantManager


	@property
	def AliceWatchManager(self) -> AliceWatchManager:  # NOSONAR
		return SM.SuperManager.getInstance().AliceWatchManager


	@property
	def AudioServer(self) -> AudioManager:  # NOSONAR
		return SM.SuperManager.getInstance().AudioManager


	@property
	def DialogManager(self) -> DialogManager:  # NOSONAR
		return SM.SuperManager.getInstance().DialogManager


	@property
	def LocationManager(self) -> LocationManager:  # NOSONAR
		return SM.SuperManager.getInstance().LocationManager


	@property
	def WakewordManager(self) -> WakewordManager:  # NOSONAR
		return SM.SuperManager.getInstance().WakewordManager


	@property
	def NodeRedManager(self) -> NodeRedManager:  # NOSONAR
		return SM.SuperManager.getInstance().NodeRedManager


	@property
	def WidgetManager(self) -> WidgetManager:  # NOSONAR
		return SM.SuperManager.getInstance().WidgetManager


	@property
	def StateManager(self) -> StateManager:  # NOSONAR
		return SM.SuperManager.getInstance().StateManager


	@property
	def WebUIManager(self) -> WebUIManager:  # NOSONAR
		return SM.SuperManager.getInstance().WebUiManager


	@property
	def SubprocessManager(self) -> SubprocessManager:  # NOSONAR
		return SM.SuperManager.getInstance().SubprocessManager


	@property
	def WebUINotificationManager(self) -> WebUINotificationManager:  # NOSONAR
		return SM.SuperManager.getInstance().WebUINotificationManager

	@property
	def BugReportManager(self) -> BugReportManager:  # NOSONAR
		return SM.SuperManager.getInstance().BugReportManager
