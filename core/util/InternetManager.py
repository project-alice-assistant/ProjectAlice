import requests

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


	def checkOnlineState(self, addr: str = 'http://clients3.google.com/generate_204'):
		try:
			req = requests.get(addr)
			if req.status_code == 204:
				if not self._online:
					self.broadcast(method='onInternetConnected', exceptions=[self.name], propagateToModules=True)

				self._online = True
				return
		except:
			pass

		if self._online:
			self.broadcast(method='onInternetLost', exceptions=[self.name], propagateToModules=True)

		self._online = False
