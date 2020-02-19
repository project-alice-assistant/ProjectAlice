import uuid
from datetime import datetime
from pathlib import Path

from core.base.model.Manager import Manager


class SnipsAssistantManager(Manager):

	def __init__(self):
		super().__init__()
		self._assistantPath = Path(self.Commons.rootDir(), f'trained/assistants/assistant_{self.LanguageManager.activeLanguage}/assistant.json')


	def onStart(self):
		super().onStart()
		self.checkAssistant()


	def checkAssistant(self):
		self.logInfo('Checking assistant')
		if not self._assistantPath.exists():
			self.logInfo('Assistant not found, generating')


	def generateAssistant(self):
		assistant = dict()
		assistant['id'] = uuid.uuid4(),
		assistant['name'] = f'ProjectAlice_{self.LanguageManager.activeLanguage}'
		assistant['analyticsEnabled'] = False
		assistant['heartbeatEnabled'] = False
		assistant['language'] = self.LanguageManager.activeLanguage

		# Declare as google so snips doesn't try to find the snips-asr service
		assistant['asr'] = {'type': 'google'}

		assistant['platform'] = {'type': 'raspberrypi'}
		assistant['createdAt'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
		assistant['hotword'] = 'hey_snips'
		assistant['intents'] = list()
