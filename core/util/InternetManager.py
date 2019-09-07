import requests

from core.base.SuperManager import SuperManager
from core.base.model.Manager import Manager


class InternetManager(Manager):

	NAME = 'InternetManager'

	def __init__(self):
		super().__init__(self.NAME)
		self._online = False


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			self._checkOnlineState()
		else:
			self._logger.info('[{}] Configurations set to stay completly offline'.format(self.name))


	@property
	def online(self) -> bool:
		return self._online


	def onBooted(self):
		self._checkOnlineState()


	def onFullMinute(self):
		if not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			self._checkOnlineState()


	def _checkOnlineState(self, addr: str = 'http://clients3.google.com/generate_204'):
		try:
			req = requests.get(addr)
			if req.status_code == 204:
				if not self._online:
					SuperManager.getInstance().broadcast(method='onInternetConnected', exceptions=[self._name])

				self._online = True
				return
		except:
			pass

		if self._online:
			SuperManager.getInstance().broadcast(method='onInternetLost', exceptions=[self._name])

		self._online = False
