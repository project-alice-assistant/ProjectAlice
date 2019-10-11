import logging
import typing

class User:
	def __init__(self, row: typing.Any):
		self._logger 		= logging.getLogger('ProjectAlice')

		if row:
			self._name 			= row['username']
			self._accessLevel 	= row['accessLevel']
			self._state 		= row['state']
			self._lang 			= row['lang']
			self._tts 			= row['tts']
			self._ttsLanguage	= row['ttsLanguage']
			self._ttsType		= row['ttsType']
			self._ttsVoice 		= row['ttsVoice']

		self._home 			= False
		self._goingBed 		= False
		self._sleeping 		= False
		self._cooking 		= False
		self._makeUp 		= False
		self._watchingTV	= False
		self._eating 		= False

		try:
			exec(f"self._{self._state} = 'True'")
		except:
			self._logger.error(f"Invalid state \"{row['state']}\" for user \"{self._name}\"")

	@property
	def name(self) -> str:
		return self._name

	@property
	def accessLevel(self) -> str:
		return self._accessLevel

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
