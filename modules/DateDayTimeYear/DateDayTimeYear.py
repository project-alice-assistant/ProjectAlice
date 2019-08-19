# -*- coding: utf-8 -*-

from datetime import datetime

import core.base.Managers    as managers
from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession


class DateDayTimeYear(Module):
	_INTENT_GET_TIME = Intent('GetTime')
	_INTENT_GET_DATE = Intent('GetDate')
	_INTENT_GET_DAY = Intent('GetDay')
	_INTENT_GET_YEAR = Intent('GetYear')


	def __init__(self):
		self._SUPPORTED_INTENTS = [
			self._INTENT_GET_TIME,
			self._INTENT_GET_DATE,
			self._INTENT_GET_DAY,
			self._INTENT_GET_YEAR
		]

		super().__init__(self._SUPPORTED_INTENTS)


	def onMessage(self, intent: str, session: DialogSession) -> bool:
		if not self.filterIntent(intent, session):
			return False

		siteId = session.siteId
		sessionId = session.sessionId

		if intent == self._INTENT_GET_TIME:
			#managers.ModuleManager.broadcast('onDoAuth', isEvent=False, args=[session.user, siteId])
			#return True
			minutes = datetime.now().strftime('%M').lstrip('0')
			part = datetime.now().strftime('%p')

			# english has a 12 hour clock and adds oh below 10 min
			if managers.LanguageManager.activeLanguage == 'en':
				hours = datetime.now().strftime('%I').lstrip('0')
				if minutes != '' and int(minutes) < 10:
					minutes = 'oh {}'.format(minutes)
			else:
				hours = datetime.now().strftime('%H').lstrip('0')

			managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('time').format(hours, minutes, part))
		elif intent == self._INTENT_GET_DATE:
			date = datetime.now().strftime('%d %B %Y')
			date = managers.LanguageManager.localize(date)
			managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('date').format(date))
		elif intent == self._INTENT_GET_DAY:
			day = datetime.now().strftime('%A')
			day = managers.LanguageManager.localize(day)
			managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('day').format(day))
		elif intent == self._INTENT_GET_YEAR:
			year = datetime.now().strftime('%Y')
			managers.MqttServer.endTalk(sessionId, managers.TalkManager.randomTalk('day').format(year))

		return True
