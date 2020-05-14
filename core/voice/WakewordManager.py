from importlib import import_module, reload

from paho.mqtt.client import MQTTMessage

from core.base.model.Manager import Manager
from core.voice.model.WakewordEngine import WakewordEngine


class WakewordManager(Manager):

	def __init__(self):
		super().__init__()
		self._engine = None


	def onStart(self):
		super().onStart()
		self._startWakewordEngine()


	def onStop(self):
		if self._engine:
			self._engine.onStop()


	def onBooted(self):
		if self._engine:
			self._engine.onBooted()


	def onAudioFrame(self, message: MQTTMessage, siteId: str):
		if self._engine:
			self._engine.onAudioFrame(message=message, siteId=siteId)


	def _startWakewordEngine(self):
		userWakeword = self.ConfigManager.getAliceConfigByName(configName='wakewordEngine').lower()

		self._engine = None

		if userWakeword == 'porcupine':
			package = 'core.voice.model.PorcupineWakeword'
		else:
			package = 'core.voice.model.SnipsWakeword'

		module = import_module(package)
		wakeword = getattr(module, package.rsplit('.', 1)[-1])
		self._engine = wakeword()

		if not self._engine.checkDependencies():
			if self._engine.installDependencies():
				self._engine = None
			else:
				module = reload(module)
				wakeword = getattr(module, package.rsplit('.', 1)[-1])
				self._engine = wakeword()

		if self._engine is None:
			self.logFatal("Couldn't install wakeword engine, going down")
			return

		self._engine.onStart()


	@property
	def wakewordEngine(self) -> WakewordEngine:
		return self._engine
