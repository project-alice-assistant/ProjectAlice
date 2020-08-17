from importlib import import_module, reload

from paho.mqtt.client import MQTTMessage

from core.base.model.Manager import Manager
from core.dialog.model.DialogSession import DialogSession
from core.voice.model.WakewordEngine import WakewordEngine


class WakewordManager(Manager):

	def __init__(self):
		super().__init__()
		self._engine = None


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('disableSoundAndMic'):
			self._startWakewordEngine()


	def onStop(self):
		super().onStop()
		if self._engine:
			self._engine.onStop()


	def onBooted(self):
		if self._engine:
			self._engine.onBooted()


	def onAudioFrame(self, message: MQTTMessage, siteId: str):
		if self._engine:
			self._engine.onAudioFrame(message=message, siteId=siteId)


	def onHotwordToggleOn(self, siteId: str, session: DialogSession):
		if self._engine:
			self._engine.onHotwordToggleOn(siteId=siteId, session=DialogSession)


	def onHotwordToggleOff(self, siteId: str, session: DialogSession):
		if self._engine:
			self._engine.onHotwordToggleOff(siteId=siteId, session=DialogSession)


	def _startWakewordEngine(self):
		userWakeword = self.ConfigManager.getAliceConfigByName(configName='wakewordEngine').lower()

		self._engine = None

		package = f'core.voice.model.{userWakeword.title()}Wakeword'
		module = import_module(package)
		wakeword = getattr(module, package.rsplit('.', 1)[-1])
		self._engine = wakeword()

		if not self._engine.checkDependencies():
			if not self._engine.installDependencies():
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


	def disableEngine(self):
		if self._engine:
			self._engine.onStop()


	def enableEngine(self):
		if self._engine:
			self._engine.onStart()
		else:
			self._startWakewordEngine()
			if self._engine:
				self._engine.onBooted()


	def restartEngine(self):
		if self._engine:
			self._engine.onStop()
		self.enableEngine()


	def toggleEngine(self):
		if not self._engine:
			return

		if self._engine.enabled:
			self._engine.onStop()
		else:
			self._engine.onStart()
