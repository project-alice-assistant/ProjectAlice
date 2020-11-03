import requests

from core.base.model.Manager import Manager
from core.commons import constants


class InternetManager(Manager):

	def __init__(self):
		super().__init__()
		self._online = False
		self._checkThread = None
		self._checkFrequency = 2


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			self.checkOnlineState(silent=True)
			# 20 seconds is the max, 2 seconds the minimum
			# We have 10 positions in the config (from 1 to 10) So the frequency = max / 10 * setting = 2 * setting
			internetQuality = self.ConfigManager.getAliceConfigByName('internetQuality') or 1
			self._checkFrequency = internetQuality * 2
			self._checkThread = self.ThreadManager.newThread(name='internetCheckThread', target=self.checkInternet)
		else:
			self.logInfo('Configurations set to stay completly offline')


	@property
	def online(self) -> bool:
		return self._online


	def onBooted(self):
		self.checkOnlineState()


	def checkInternet(self):
		self.checkOnlineState()
		self.ThreadManager.doLater(interval=self._checkFrequency, func=self.checkInternet)


	def checkOnlineState(self, addr: str = 'https://clients3.google.com/generate_204', silent: bool = False) -> bool:
		if self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			return False

		try:
			online = requests.get(addr).status_code == 204
		except:
			online = False

		if silent:
			self._online = online
			return online

		if self._online and not online:
			self._online = False
			self.broadcast(method=constants.EVENT_INTERNET_LOST, exceptions=[self.name], propagateToSkills=True)
		elif not self._online and online:
			self._online = True
			self.broadcast(method=constants.EVENT_INTERNET_CONNECTED, exceptions=[self.name], propagateToSkills=True)

		return online
