import requests
from requests.exceptions import RequestException

from core.base.model.Manager import Manager


class InternetManager(Manager):

	NAME = 'InternetManager'

	def __init__(self):
		super().__init__(self.NAME)
		self._online = False


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			self.checkOnlineState()
		else:
			self.logInfo('Configurations set to stay completly offline')


	@property
	def online(self) -> bool:
		return self._online


	def onBooted(self):
		self.checkOnlineState()


	def onFullMinute(self):
		if not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			self.checkOnlineState()


	def checkOnlineState(self, addr: str = 'http://clients3.google.com/generate_204') -> bool:
		try:
			online = requests.get(addr).status_code == 204
		except RequestException:
			online = False
		
		if self._online and not online:
			self._online = False
			self.broadcast(method='onInternetLost', exceptions=[self.name], propagateToSkills=True)
		elif not self._online and online:
			self._online = True
			self.broadcast(method='onInternetConnected', exceptions=[self.name], propagateToSkills=True)
		return online
