from typing import Any, Optional

from core.base.model.Manager import Manager
from core.user.model.AccessLevels import AccessLevel
from core.user.model.User import User


class UserManager(Manager):

	NAME = 'UserManager'

	DATABASE = {
		'users': [
			'id INTEGER PRIMARY KEY',
			'username TEXT NOT NULL',
			'state TEXT NOT NULL',
			'accessLevel TEXT NOT NULL',
			'pin INTEGER',
			'lang TEXT',
			'tts TEXT',
			'ttsLanguage TEXT',
			'ttsType TEXT',
			'ttsVoice TEXT'
		]
	}


	def __init__(self):
		super().__init__(self.NAME, self.DATABASE)
		self._users = dict()


	def onStart(self):
		super().onStart()
		self._loadUsers()
		self.logInfo(f'- Loaded {len(self._users)} users')


	def _loadUsers(self):
		rows = self.databaseFetch(tableName='users', query='SELECT * FROM :__table__', method='all')
		for row in rows:
			self._users[row['username']] = User(row)


	@property
	def users(self) -> dict:
		return self._users


	# noinspection SqlResolve
	def addNewUser(self, name: str, access: str = 'guest', state: str = 'home'):
		insertId = self.databaseInsert(tableName='users',
									   query='INSERT INTO :__table__ (username, accessLevel, state, lang) VALUES (:username, :accessLevel, :state, :lang)',
									   values={'username': name.lower(), 'accessLevel': access, 'state': state, 'lang': self.LanguageManager.activeLanguageAndCountryCode})
		if insertId > -1:
			self._users[name] = User({
				'username': name.title(),
				'accessLevel': access,
				'state': state,
				'lang': self.LanguageManager.activeLanguageAndCountryCode,
				'tts': '',
				'ttsLanguage': '',
				'ttsType': '',
				'ttsVoice': ''
			})


	def getUserAccessLevel(self, username: str) -> Optional[Any]:
		if not username in self._users:
			return None

		return self._users[username].accessLevel


	def getUser(self, username: str) -> Optional[User]:
		return self._users.get(username, None)


	def getAllUserNames(self, skipGuests: bool = True) -> list:
		"""
			Return all users
			:return: list
		"""
		if skipGuests:
			users = [k for k in self._users if self._users[k] != 'guest']
		else:
			users = [k for k in self._users]

		return users


	def checkIfAllUser(self, state: str) -> bool:
		"""
		Checks if the given state applies to all users (except for guests)
		:param state: the state to check
		:return: boolean
		"""

		if not self._users:
			return False

		userNames = self.getAllUserNames()

		for username in userNames:
			if self._users[username].state != state:
				return False

		return True


	def checkIfUser(self, user: str, state: str) -> bool:
		"""
		Checks if the given state applies to the user
		:param user: str
		:param state: the state to check
		:return: boolean
		"""
		return self._users[user].state == state


	def goingBed(self, user: str = 'all'):
		if user == 'all':
			for user in self._users:
				self._users[user].state('goingBed')
		else:
			self._users[user].home = True
			self._users[user].goingBed = True
			self._users[user].sleeping = False


	def sleeping(self, user: str = 'all'):
		if user == 'all':
			for user in self._users:
				self._users[user].state('sleeping')
		else:
			self._users[user].home = True
			self._users[user].goingBed = False
			self._users[user].sleeping = True


	def wakeup(self, user: str = 'all'):
		if user == 'all':
			for user in self._users:
				self._users[user].state('home')
		else:
			self._users[user].home = True
			self._users[user].goingBed = False
			self._users[user].sleeping = False


	def leftHome(self, user: str = 'all'):
		if user == 'all':
			for user in self._users:
				self._users[user].state('out')
		else:
			self._users[user].home = False
			self._users[user].goingBed = False
			self._users[user].sleeping = False


	def home(self, user: str = 'all'):
		if user == 'all':
			for user in self._users:
				self._users[user].state('home')
		else:
			self._users[user].home = True
			self._users[user].goingBed = False
			self._users[user].sleeping = False


	def hasAccessLevel(self, user: str, requiredAccessLevel: str) -> bool:
		try:
			_ = AccessLevel[requiredAccessLevel.upper()]
		except KeyError:
			self.logError(f'Was asked to check access level but accesslevel "{requiredAccessLevel}" doesn\'t exist')
			return False


		if user.lower() not in self._users:
			self.logError(f'Was asked to check access level but user "{user}" doesn\'t exist')
			return False

		return AccessLevel[self._users[user.lower()].accessLevel.upper()].value <= AccessLevel[requiredAccessLevel.upper()].value
