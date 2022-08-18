#  Copyright (c) 2021
#
#  This file, DialogManager.py, is part of Project Alice.
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

import json
import uuid
from paho.mqtt.client import MQTTMessage
from pathlib import Path
from threading import Timer
from typing import Dict, Optional, Set

from core.base.model.Manager import Manager
from core.commons import constants
from core.commons.model.PartOfDay import PartOfDay
from core.device.model.DeviceAbility import DeviceAbility
from core.dialog.model.DialogSession import DialogSession
from core.voice.WakewordRecorder import WakewordRecorderState


class DialogManager(Manager):
	DATABASE = {
		'notRecognizedIntents': [
			'text TEXT NOT NULL'
		]
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)
		self._sessionsById: Dict[str: DialogSession] = dict()
		self._sessionsByDeviceUids: Dict[str: DialogSession] = dict()
		self._endedSessions: Dict[str: DialogSession] = dict()
		self._feedbackSounds: Dict[str: bool] = dict()
		self._sessionTimeouts: Dict[str, Timer] = dict()
		self._revivePendingSessions: Dict[str, DialogSession] = dict()

		self._disabledByDefaultIntents = set()
		self._enabledByDefaultIntents = set()

		self._captureFeedback = True


	def newSession(self, deviceUid: str, user: str = constants.UNKNOWN_USER, message: MQTTMessage = None, increaseTimeout: int = 0) -> DialogSession:
		session = DialogSession(deviceUid=deviceUid, user=user, sessionId=str(uuid.uuid4()), increaseTimeout=increaseTimeout)

		if message:
			session.update(message)

		self._sessionsById[session.sessionId] = session
		self._sessionsByDeviceUids[deviceUid] = session
		return session


	def newTempSession(self, message: MQTTMessage = None) -> DialogSession:
		deviceUid = self.Commons.parseDeviceUid(message)
		session = self.newSession(deviceUid=deviceUid, message=message)
		self.startSessionTimeout(sessionId=session.sessionId, tempSession=True)
		return session


	def onWakeword(self, deviceUid: str, user: str = constants.UNKNOWN_USER):
		self.onHotword(deviceUid=deviceUid, user=user)


	def onHotword(self, deviceUid: str, user: str = constants.UNKNOWN_USER):
		if self.WakewordRecorder.state != WakewordRecorderState.IDLE:
			return

		self.logDebug(f'Wakeword detected by **{self.DeviceManager.getDevice(uid=deviceUid).displayName}**')

		self._endedSessions[deviceUid] = self._sessionsById.pop(deviceUid, None)

		session = self.newSession(deviceUid=deviceUid, user=user)
		redQueen = self.SkillManager.getSkillInstance('RedQueen')
		if redQueen and not redQueen.inTheMood(session):
			return

		# Turn off the wakeword component
		self.MqttManager.publish(
			topic=constants.TOPIC_HOTWORD_TOGGLE_OFF,
			payload={
				'siteId'   : deviceUid,
				'sessionId': session.sessionId
			}
		)
		# Personalise the notification if able to
		talkNotification = self.TalkManager.randomTalk(talk='notification', skill='system')
		if session.user != constants.UNKNOWN_USER:
			talkNotification = talkNotification.format(session.user)
		else:
			talkNotification = talkNotification.format('')

		# Play notification if needed
		if self._feedbackSounds.get('deviceUid', True):
			self.MqttManager.publish(
				topic=constants.TOPIC_START_SESSION,
				payload={
					'siteId'    : deviceUid,
					'init'      : {
						'type'                   : 'action',
						'text'                   : talkNotification,
						'sendIntentNotRecognized': True,
						'canBeEnqueued'          : False,
						'isHotwordNotification'  : True
					},
					'customData': json.dumps(dict())
				})
		else:
			self.onSayFinished(session=session, uid=str(uuid.uuid4()))


	def onSayFinished(self, session: DialogSession, uid: str = None):
		"""
		Triggers when a Tts say has finished playing.
		If the session has not yet ended and is currently in dialog, we start listening again
		:param uid:
		:param session:
		:return:
		"""

		if not session or session.hasEnded:
			return

		if session.isEnding and 0 < session.notUnderstood < int(self.ConfigManager.getAliceConfigByName('notUnderstoodRetries')):
			session.isEnding = False
			self.SkillManager.getSkillInstance('AliceCore').askUpdateUtterance(session=session)
			return

		if not session.keptOpen and session.isEnding or session.isNotification:
			session.payload['text'] = ''
			self.onEndSession(session=session, reason='nominal')
		else:
			if not session.hasStarted:
				self.onStartSession(
					deviceUid=session.deviceUid,
					payload=dict()
				)
			else:
				self.startSessionTimeout(sessionId=session.sessionId)

				if not session.textInput:
					self.MqttManager.publish(
						topic=constants.TOPIC_ASR_TOGGLE_ON
					)

					self.MqttManager.publish(
						topic=constants.TOPIC_ASR_START_LISTENING,
						payload={
							'siteId'   : session.deviceUid,
							'sessionId': session.sessionId
						}
					)


	def startSessionTimeout(self, sessionId: str, tempSession: bool = False, delay: float = 0.0):
		self.cancelSessionTimeout(sessionId=sessionId)

		self._sessionTimeouts[sessionId] = self.ThreadManager.newTimer(
			interval=self.ConfigManager.getAliceConfigByName('sessionTimeout') + delay + self._sessionsById[sessionId].increaseTimeout,
			func=self.sessionTimeout,
			kwargs={
				'sessionId'  : sessionId,
				'tempSession': tempSession
			}
		)


	def cancelSessionTimeout(self, sessionId: str):
		timer = self._sessionTimeouts.pop(sessionId, None)
		if timer:
			timer.cancel()


	def sessionTimeout(self, sessionId: str, tempSession: bool = False):
		"""
		Session has timed out
		:param tempSession:
		:param sessionId:
		:return:
		"""
		session = self.getSession(sessionId)
		if not session:
			return

		if tempSession:
			self.removeSession(sessionId=sessionId)
			return

		session.payload['text'] = ''
		self.onEndSession(session=session, reason='timeout')


	def onSessionStarted(self, session: DialogSession):
		"""
		Session has started, enable Asr and tell it to listen
		:param session:
		:return:
		"""
		self.startSessionTimeout(sessionId=session.sessionId)
		session.hasStarted = True


	def onCaptured(self, session: DialogSession):
		"""
		Asr has captured text, tell it to stop listening
		:param session:
		:return:
		"""
		self.startSessionTimeout(sessionId=session.sessionId)

		self.MqttManager.publish(
			topic=constants.TOPIC_ASR_STOP_LISTENING,
			payload={
				'siteId'   : session.deviceUid,
				'sessionId': session.sessionId
			}
		)

		cancel = self.LanguageManager.getStrings(
			skill='system',
			key='cancelIntent'
		)

		if session.payload['text'].lower() in cancel:
			session.payload['text'] = ''
			self.onEndSession(session=session, reason='abortedByUser')
			return

		if self._captureFeedback and not session.textOnly and not session.textInput and self.Commons.partOfTheDay() != PartOfDay.SLEEPING.value:
			self.MqttManager.publish(
				topic=constants.TOPIC_PLAY_BYTES.format(session.deviceUid).replace('#', session.sessionId),
				payload=bytearray(Path(f'system/sounds/{self.LanguageManager.activeLanguage}/end_of_input.wav').read_bytes())
			)

		# If we've set the filter to a random answer, forge the session and publish an intent captured as UserRandomAnswer
		if session.intentFilter and session.intentFilter[-1] == 'UserRandomAnswer':
			self.forgeUserRandomAnswer(session=session)
			return

		self.MqttManager.publish(
			topic=constants.TOPIC_NLU_QUERY,
			payload={
				'input'       : session.payload['text'],
				'intentFilter': session.intentFilter if session.intentFilter else list(self._enabledByDefaultIntents),
				'sessionId'   : session.sessionId
			}
		)

		skill = self.SkillManager.getSkillInstance('ContextSensitive')
		if skill:
			skill.addUserChat(text=session.payload['text'], deviceUid=session.deviceUid)


	def forgeUserRandomAnswer(self, session: DialogSession):
		"""
		Forges a session and sends an onIntentParsed as if an intent was captured
		:param session:
		:return:
		"""
		if 'text' in session.payload:
			session.payload['input'] = session.payload['text']
		session.payload.setdefault('intent', dict())
		session.payload['intent']['intentName'] = 'UserRandomAnswer'
		session.payload['intent']['confidenceScore'] = 1.0
		session.payload['alternatives'] = list()
		session.payload['slots'] = list()
		self.onIntentParsed(session)


	def onIntentParsed(self, session: DialogSession):
		"""
		The NLU has parsed an intent, send that intent
		:param session:
		:return:
		"""
		self.startSessionTimeout(sessionId=session.sessionId)

		self.MqttManager.publish(
			topic=f'hermes/intent/{session.payload["intent"]["intentName"]}',
			payload={
				'sessionId'    : session.sessionId,
				'customData'   : json.dumps(session.customData),
				'siteId'       : session.deviceUid,
				'input'        : session.payload['input'],
				'intent'       : session.payload['intent'],
				'slots'        : session.payload['slots'],
				'asrTokens'    : json.dumps(list()),
				'asrConfidence': session.payload['intent']['confidenceScore'],
				'alternatives' : session.payload['alternatives']
			}
		)


	def onNluIntentNotRecognized(self, session: DialogSession):
		"""
		NLU did not recognize any intent
		:param session:
		:return:
		"""
		# If we've set the filter to a random answer, forge the session and publish an intent captured as UserRandomAnswer
		if session.intentFilter and session.intentFilter[-1] == 'UserRandomAnswer':
			self.forgeUserRandomAnswer(session=session)
			return

		self.MqttManager.publish(
			topic=constants.TOPIC_INTENT_NOT_RECOGNIZED,
			payload={
				'siteId'    : session.deviceUid,
				'customData': json.dumps(session.customData),
				'sessionId' : session.sessionId,
				'input'     : session.payload['input']
			}
		)


	def onNluError(self, session: DialogSession):
		"""
		NLU reported an error
		:param session:
		:return:
		"""
		if not 'error' in session.payload:
			return

		self.logWarning(f'NLU query failed with: {session.payload["error"]}')
		session.payload['text'] = ''
		self.onEndSession(session=session, reason='error')


	def onStartSession(self, deviceUid: str, payload: dict):
		"""
		Starts a new session
		:param deviceUid:
		:param payload:
		:return:
		"""

		session = self._sessionsByDeviceUids.get(deviceUid, None)
		if not session:
			# The session was started programmatically, we need to create one
			session = self.newSession(deviceUid=deviceUid)
		else:
			if session.hasStarted and not session.hasEnded and 'init' in payload and payload['init'].get('canBeEnqueued', True):
				self.ThreadManager.doLater(interval=1, func=self.onStartSession, kwargs={'deviceUid': deviceUid, 'payload': payload})
				return

		hotwordNotification = False

		if 'init' in payload:
			if payload['init']['type'] == 'notification':
				session.isNotification = True
				session.inDialog = False
			else:
				session.isNotification = False
				session.inDialog = True

			if 'isHotwordNotification' in payload['init'] and payload['init']['isHotwordNotification']:
				hotwordNotification = True

		self.MqttManager.publish(
			topic=constants.TOPIC_SESSION_STARTED,
			payload={
				'siteId'    : deviceUid,
				'sessionId' : session.sessionId,
				'customData': json.dumps(dict())
			}
		)
		init = payload.get('init', False)
		if init:
			text = init.get('text', '')
			if not text:
				randomText_skill = init.get('skill', '')
				randomText_talk = init.get('talk', '')
				randomText_replace = init.get('replace', [])
				if randomText_skill and randomText_talk:
					text = self.TalkManager.randomTalk(skill=randomText_skill, talk=randomText_talk)
					if randomText_replace:
						text = text.format(*randomText_replace)

			if text:
				self.MqttManager.publish(
					topic=constants.TOPIC_TTS_SAY,
					payload={
						'text'                 : text,
						'lang'                 : self.LanguageManager.activeLanguageAndCountryCode,
						'siteId'               : deviceUid,
						'sessionId'            : session.sessionId,
						'uid'                  : str(uuid.uuid4()),
						'isHotwordNotification': hotwordNotification
					}
				)


	def onContinueSession(self, session: DialogSession):
		if not session.hasStarted:
			self.onStartSession(
				deviceUid=session.deviceUid,
				payload=session.payload
			)

		self.startSessionTimeout(sessionId=session.sessionId)
		session.inDialog = True

		if 'text' in session.payload and session.payload['text']:
			self.MqttManager.publish(
				topic=constants.TOPIC_TTS_SAY,
				payload={
					'text'     : session.payload['text'],
					'lang'     : self.LanguageManager.activeLanguageAndCountryCode,
					'siteId'   : session.deviceUid,
					'sessionId': session.sessionId
				}
			)


	def onEndSession(self, session: DialogSession, reason: str = 'nominal'):
		self.enableCaptureFeedback()
		text = session.payload.get('text', '')

		if text:
			session.isEnding = True
			self.cancelSessionTimeout(sessionId=session.sessionId)

			self.MqttManager.publish(
				topic=constants.TOPIC_TTS_SAY,
				payload={
					'text'     : session.payload['text'],
					'lang'     : self.LanguageManager.activeLanguageAndCountryCode,
					'siteId'   : session.deviceUid,
					'sessionId': session.sessionId
				}
			)
		else:
			self.MqttManager.publish(
				topic=constants.TOPIC_SESSION_ENDED,
				payload={
					'siteId'     : session.deviceUid,
					'sessionId'  : session.sessionId,
					'customData' : json.dumps(session.customData),
					'termination': {
						'reason': reason
					}
				}
			)


	def onSessionEnded(self, session: DialogSession):
		"""
		Session has ended, enable hotword capture and disable Asr
		:param session:
		:return:
		"""
		session.hasEnded = True

		self.MqttManager.publish(
			topic=constants.TOPIC_ASR_TOGGLE_OFF
		)

		self.MqttManager.publish(
			topic=constants.TOPIC_HOTWORD_TOGGLE_ON,
			payload={
				'siteId'   : session.deviceUid,
				'sessionId': session.sessionId
			}
		)

		self.removeSession(sessionId=session.sessionId)


	def onSessionError(self, session: DialogSession):
		if self.Commons.partOfTheDay() == PartOfDay.SLEEPING.value:
			return

		if not session.textOnly and not session.textInput:
			self.MqttManager.publish(
				topic=constants.TOPIC_PLAY_BYTES.format(session.deviceUid).replace('#', session.sessionId),
				payload=bytearray(Path(f'system/sounds/{self.LanguageManager.activeLanguage}/error.wav').read_bytes())
			)


	def toggleFeedbackSound(self, state: str, deviceUid: str = constants.ALL):
		topic = constants.TOPIC_TOGGLE_FEEDBACK_ON if state == 'on' else constants.TOPIC_TOGGLE_FEEDBACK_OFF

		if deviceUid == constants.ALL:
			devices = self.DeviceManager.getDevicesWithAbilities(abilities=[DeviceAbility.PLAY_SOUND, DeviceAbility.CAPTURE_SOUND])
			for device in devices:
				self.MqttManager.publish(topic=topic, payload={'siteId': device.uid})

		else:
			self.MqttManager.publish(topic=topic, payload={'siteId': deviceUid})


	def onToggleFeedbackOn(self, deviceUid: str):
		self._feedbackSounds[deviceUid] = True


	def onToggleFeedbackOff(self, deviceUid: str):
		self._feedbackSounds[deviceUid] = False


	def onIntentNotRecognized(self, session: DialogSession):
		if not session.input:
			return

		session.previousInput = session.input
		self.databaseInsert(
			tableName='notRecognizedIntents',
			values={
				'text': session.input
			}
		)


	def getSession(self, sessionId: str) -> Optional[DialogSession]:
		return self._sessionsById.get(sessionId, None)


	def uidBusy(self, uid: str) -> bool:
		session = self._sessionsByDeviceUids.get(uid, None)
		if session:
			return True
		else:
			return False


	def removeSession(self, sessionId: str):
		self.cancelSessionTimeout(sessionId=sessionId)

		session = self._sessionsById.pop(sessionId, None)
		if not session:
			return

		self._endedSessions[sessionId] = session
		self._sessionsByDeviceUids.pop(session.deviceUid, None)


	def increaseSessionTimeout(self, session: DialogSession, interval: float):
		"""
		This is used by the Tts, so that the timeout is set to the duration of the speech at least
		:param session:
		:param interval:
		:return:
		"""
		if session.sessionId not in self._sessionsById:
			return

		self.startSessionTimeout(sessionId=session.sessionId, delay=interval)


	@property
	def sessions(self) -> Dict[str, DialogSession]:
		return self._sessionsById


	@property
	def sessionsBySites(self) -> Dict[str, DialogSession]:
		return self._sessionsByDeviceUids


	def addDisabledByDefaultIntent(self, intent: str):
		self._disabledByDefaultIntents.add(intent)
		# Remove it from enabled intents in case it exists
		if intent in self._enabledByDefaultIntents:
			self._enabledByDefaultIntents.remove(intent)


	def addEnabledByDefaultIntent(self, intent: str):
		self._enabledByDefaultIntents.add(intent)


	def cleanNotRecognizedIntent(self, text: str):
		self.DatabaseManager.delete(
			tableName='notRecognizedIntents',
			callerName=self.name,
			values={
				'text': text
			}
		)


	def getEnabledByDefaultIntents(self) -> Set:
		return self._enabledByDefaultIntents


	def disableCaptureFeedback(self):
		self._captureFeedback = False


	def enableCaptureFeedback(self):
		self._captureFeedback = True
