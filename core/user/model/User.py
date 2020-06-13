import typing

import bcrypt

from core.base.model.ProjectAliceObject import ProjectAliceObject


class User(ProjectAliceObject):

	def __init__(self, row: typing.Optional[dict]):
		super().__init__()

		#TODO is it correct to init these values only when row exists?
		# -> will throw exception when property is called or should they be
		# inited to None instead
		# how about replace with: row.get('id',None)
		if row:
			self._id = row['id']
			self._name = row['username']
			self._accessLevel = row['accessLevel']
			self._state = row['state']
			self._pin = row['pin']
			self._lang = row['lang']
			self._tts = row['tts']
			self._ttsLanguage = row['ttsLanguage']
			self._ttsType = row['ttsType']
			self._ttsVoice = row['ttsVoice']
			self._apiToken = row['apiToken']

		self._home = False
		self._goingBed = False
		self._sleeping = False
		self._cooking = False
		self._makeUp = False
		self._watchingTV = False
		self._eating = False

		try:
			exec(f"self._{self._state} = 'True'")
		except:
			self.logError(f"Invalid state \"{row['state']}\" for user \"{self._name}\"")

		# flask login reqs
		self._isAuthenticated = False
		self._isActive = True
		self._isAnonymous = False


	def toJson(self) -> dict:
		return {
			'id'         : self._id,
			'name'       : self._name,
			'accessLevel': self._accessLevel,
			'state'      : self._state,
			'lang'       : self._lang,
			'tts'        : self._tts,
			'ttsLanguage': self._ttsLanguage,
			'ttsType'    : self._ttsType,
			'ttsVoice'   : self._ttsVoice
		}


	@property
	def id(self) -> int:
		return self._id


	@property
	def name(self) -> str:
		return self._name


	@property
	def accessLevel(self) -> str:
		return self._accessLevel


	@property
	def pin(self) -> bytes:
		return self._pin


	@property
	def state(self) -> str:
		return self._state


	@property
	def lang(self) -> str:
		return self._lang


	@property
	def tts(self) -> str:
		return self._tts


	@property
	def ttsLanguage(self) -> str:
		return self._ttsLanguage


	@property
	def ttsType(self) -> str:
		return self._ttsType


	@property
	def ttsVoice(self) -> str:
		return self._ttsVoice


	@property
	def apiToken(self) -> str:
		return self._apiToken


	@apiToken.setter
	def apiToken(self, val: str):
		self._apiToken = val


	@property
	def home(self) -> bool:
		return self._home


	@property
	def goingBed(self) -> bool:
		return self._goingBed


	@property
	def sleeping(self) -> bool:
		return self._sleeping


	@property
	def cooking(self) -> bool:
		return self._cooking


	@property
	def makeUp(self) -> bool:
		return self._makeUp


	@property
	def watchingTV(self) -> bool:
		return self._watchingTV


	@property
	def eating(self) -> bool:
		return self._eating


	@name.setter
	def name(self, value: str):
		self._name = value


	@accessLevel.setter
	def accessLevel(self, value: str):
		self._accessLevel = value


	@pin.setter
	def pin(self, value: bytes):
		self._pin = value


	@state.setter
	def state(self, value: str):
		self._state = value


	@home.setter
	def home(self, value: bool):
		self._home = value


	@goingBed.setter
	def goingBed(self, value: bool):
		self._goingBed = value


	@sleeping.setter
	def sleeping(self, value: bool):
		self._sleeping = value


	@cooking.setter
	def cooking(self, value: bool):
		self._cooking = value


	@makeUp.setter
	def makeUp(self, value: bool):
		self._makeUp = value


	@watchingTV.setter
	def watchingTV(self, value: bool):
		self._watchingTV = value


	@eating.setter
	def eating(self, value: bool):
		self._eating = value


	def checkPassword(self, password: str) -> bool:
		if self.pin is None:
			self.logWarning('No pin defined for this user')
			return False

		return bcrypt.checkpw(str(password).encode(), self.pin)


	@property
	def isAuthenticated(self) -> bool:
		return self.is_authenticated


	@isAuthenticated.setter
	def isAuthenticated(self, value: bool):
		self.is_authenticated = value


	@property
	def isActive(self) -> bool:
		return self.is_active


	@property
	def isAnonymous(self) -> bool:
		return self.is_anonymous


	# Flask login reqs
	# Do not rename to our standards!!!
	def get_id(self) -> int:
		return self._id


	@property
	def is_authenticated(self) -> bool:
		return self._isAuthenticated


	@is_authenticated.setter
	def is_authenticated(self, value: bool):
		self._isAuthenticated = value


	@property
	def is_active(self) -> bool:
		return self._isActive


	@property
	def is_anonymous(self) -> bool:
		return self._isAnonymous
