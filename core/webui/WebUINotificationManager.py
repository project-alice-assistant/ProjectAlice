#  Copyright (c) 2021
#
#  This file, WebUINotificationManager.py, is part of Project Alice.
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
#  Last modified: 2021.10.13 at 15:06:55 CEST

import json
from typing import Dict, Union

from core.base.model.Manager import Manager
from core.commons import constants
from core.webui.model.UINotificationType import UINotificationType


class WebUINotificationManager(Manager):
	NOTIFICATIONS_TABLE = 'webUINotifications'

	DATABASE = {
		NOTIFICATIONS_TABLE: [
			'id INTEGER PRIMARY KEY',  # NOSONAR
			'type TEXT NOT NULL',
			'read INTEGER NOT NULL DEFAULT 0',
			'title TEXT NOT NULL',
			'body TEXT NOT NULL',
			'key TEXT NULL',
			'options TEXT NULL DEFAULT "{}"'
		]
	}


	def __init__(self):
		self._notifications = dict()
		self._keysToIds = dict()
		super().__init__(databaseSchema=self.DATABASE)


	def onStart(self):
		super().onStart()
		# noinspection SqlResolve
		notifications = self.databaseFetch(tableName=self.NOTIFICATIONS_TABLE, query=f'SELECT * FROM :__table__ WHERE read = 0')
		for notification in notifications:
			self._notifications[notification['id']] = notification


	def onBooted(self):
		self.publishAllNotifications()


	@property
	def notifications(self) -> dict:
		return self._notifications


	def newNotification(self, typ: Union[UINotificationType, str], notification: Union[str, Dict[str, str]], key: str = None, replaceTitle: list = None, replaceBody: list = None, options: dict = None, deviceUid: str = 'all', allowDuplicates: bool = False):
		"""
		Stores and sends a UI notification
		:param typ: The notification type, either as the enum or a string when coming from the database
		:param notification: the json object key of the notification to send in case of system notification or a dict containing the title and the body of the notification
		:param key: A notification key. If provided, it will be used on the UI as div id. It's useful for notifications that get updated over time
		:param replaceTitle: A list of strings to format the original title string
		:param replaceBody: A list of strings to format the original body string
		:param options: Options in a form of a dict for this notification, used by the UI
		:param deviceUid: If only a certain device should get this notification
		:param allowDuplicates: If false, by default, do not add a same notification more than once
		:return:
		"""

		if isinstance(notification, str):
			notification = self.LanguageManager.getWebUINotification(notification)
			if not notification:
				return

		title = notification['title']
		if replaceTitle:
			title = title.format(replaceTitle)

		body = notification['body']
		if replaceBody:
			body = body.format(*replaceBody)

		if isinstance(typ, UINotificationType):
			typ = typ.value

		if not options:
			options = dict()

		values = {
			'type'   : typ,
			'title'  : title,
			'body'   : body,
			'options': json.dumps(options),
			'key'    : key
		}

		if key and key in self._keysToIds:
			notificationId = self._keysToIds[key]
			self.DatabaseManager.update(tableName=self.NOTIFICATIONS_TABLE, callerName=self.name, values=values, row=('id', notificationId))
		else:
			notificationId = self.databaseInsert(tableName=self.NOTIFICATIONS_TABLE, values=values)
			self._keysToIds[key] = notificationId
			self.logInfo(f'Adding notification[{notificationId}]: {title}')

		self.publishNotification(notificationId=notificationId, typ=typ, title=title, body=body, key=key, options=options, deviceUid=deviceUid)


	def publishAllNotifications(self, deviceUid: str = 'all'):
		"""
		Publishes all unread notifications
		:param deviceUid: if targeted to a specific device
		:return: none
		"""
		for notification in self._notifications.values():
			self.publishNotification(
				notificationId=notification['id'],
				typ=notification['type'],
				title=notification['title'],
				body=notification['body'],
				key=notification['key'],
				options=json.loads(notification['options']),
				deviceUid=deviceUid
			)


	def publishNotification(self, notificationId: int, typ: str, title: str, body: str, key: str = None, options: dict = None, deviceUid: str = 'all'):
		"""
		Publishes the notification over MQTT
		:param notificationId: database id
		:param typ: the notification typ as a string
		:param title: notification title
		:param body: notification content
		:param key: the key is used for notifications that can update over time, to differentiate them
		:param options: for future purposes
		:param deviceUid: if target to a specific device only
		:return:
		"""
		payload = {
			'id'       : notificationId,
			'type'     : typ,
			'title'    : title,
			'text'     : body,
			'key'      : key,
			'options'  : options if options else '{}',
			'deviceUid': deviceUid
		}

		self.MqttManager.publish(topic=constants.TOPIC_UI_NOTIFICATION, payload=payload)


	def markAsRead(self, notificationId: int):
		"""
		Marks the notification as read in the database
		:param notificationId: the notification id to mark
		:return:
		"""
		self.DatabaseManager.update(tableName=self.NOTIFICATIONS_TABLE, callerName=self.name, values={'read': 1}, row=('id', notificationId))
		notification = self._notifications.pop(notificationId, None)
		if notification:
			self._keysToIds.pop(notification.get('key', 'dummy'), None)


	def onSkillUpdated(self, skill: str):
		self.newNotification(
			typ=UINotificationType.INFO,
			notification='skillUpdated',
			key=f'skillUpdate_{skill}',
			replaceBody=[skill, self.SkillManager.getSkillInstance(skillName=skill).version]
		)


	def onSkillInstalled(self, skill: str):
		self.newNotification(
			typ=UINotificationType.INFO,
			notification='skillInstalled',
			key=f'skillUpdate_{skill}',
			replaceBody=[skill]
		)
