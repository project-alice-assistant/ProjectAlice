import time
import uuid
from pathlib import Path

import requests
import tempfile

from core.base.model.Manager import Manager
from core.commons import constants
from core.snips.model.SnipsConsoleUser import SnipsConsoleUser
from core.snips.model.SnipsTrainingStatus import SnipsTrainingType, TrainingStatusResponse


class SnipsConsoleManager(Manager):

	def __init__(self):
		super().__init__()

		self._connected = False
		self._tries = 0
		self._user = None

		self._headers = {
			'Accept'      : 'application/json',
			'Content-Type': 'application/json'
		}


	def onStart(self):
		super().onStart()

		if self.ConfigManager.getSnipsConfiguration('project-alice', 'console_token'):
			self.log.info('Snips console authorized')
			self._headers['Authorization'] = f"JWT {self.ConfigManager.getSnipsConfiguration('project-alice', 'console_token')}"

			self._user = SnipsConsoleUser({
				'id': self.ConfigManager.getSnipsConfiguration('project-alice', 'console_user_id'),
				'email': self.ConfigManager.getSnipsConfiguration('project-alice', 'console_user_email')
			})

			self._connected = True

		elif self.loginCredentialsAreConfigured():
			self.log.info('Snips console not authorized')
			self._login()
		else:
			self.log.warning('Snips console credentials not found')
			if not Path(self.Commons.rootDir(), '/assistant').exists():
				self.log.error('No assistant found, cannot start')
				self.ProjectAlice.onStop()
			else:
				self.log.warning('Assistant is existing, allowing to boot but functions will be restricted!')
				self.isActive = False


	def doDownload(self, skillsInfos: dict = None):
		self.log.info('Starting Snips assistant training and download procedure')
		self.ThreadManager.newEvent('SnipsAssistantDownload', onClearCallback='onSnipsAssistantDownloaded').set(skillsInfos=skillsInfos)

		projectId = self.LanguageManager.activeSnipsProjectId
		self.ThreadManager.newThread(name='SnipsAssistantDownload', target=self.download, args=[projectId])


	def loginCredentialsAreConfigured(self):
		return self.ConfigManager.getAliceConfigByName('snipsConsoleLogin') and \
			   self.ConfigManager.getAliceConfigByName('snipsConsolePassword')


	def _login(self):
		self._tries += 1
		if self._tries > 3:
			self.log.info(f'Tried to login {self._tries} times, giving up now')
			self._tries = 0
			return

		self.log.info(f"Connecting to Snips console using account {self.ConfigManager.getAliceConfigByName('snipsConsoleLogin')}")
		payload = {
			'email': self.ConfigManager.getAliceConfigByName('snipsConsoleLogin'),
			'password': self.ConfigManager.getAliceConfigByName('snipsConsolePassword')
		}

		req = self._req(url='/v1/user/auth', data=payload)
		if req.status_code == 200:
			self.log.info('Connected to Snips console. Fetching and saving access token')
			try:
				token = req.headers['authorization']
				self._user = SnipsConsoleUser(req.json()['user'])

				accessToken = self._getAccessToken(token)
				if accessToken:
					self.log.info('Saving console access token')
					self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_token', value=accessToken['token'])
					self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_alias', value=accessToken['alias'])
					self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_id', value=self._user.userId)
					self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_email', value=self._user.userEmail)

					self._headers['Authorization'] = f"JWT {accessToken['token']}"

					self._connected = True
					self._tries = 0
				else:
					raise Exception('Error fetching JWT console token')
			except Exception as e:
				self.log.error(f"Couldn't retrieve snips console token: {e}")
				self._connected = False
				return
		else:
			self.log.error(f"Couldn't connect to Snips console: {req.status_code}")
			self._connected = False


	def _getAccessToken(self, token: str) -> dict:
		alias = f'projectalice{uuid.uuid4()}'.replace('-', '')[:29]
		self._headers['Authorization'] = token
		req = self._req(url=f'/v1/user/{self._user.userId}/accesstoken', data={'alias': alias})
		if req.status_code == 201:
			return req.json()['token']
		return dict()


	def _listAssistants(self) -> dict:
		req = self._req(url='/v3/assistant', method='get', data={'userId': self._user.userId})
		return req.json()['assistants']


	def _trainAssistant(self, assistantId: str, trainingType: SnipsTrainingType):
		return self._req(url=f'/v2/training/assistant/{assistantId}', data={'trainingType': trainingType.value}, method='post')


	def _trainingStatus(self, assistantId: str) -> TrainingStatusResponse:
		req = self._req(url=f'/v2/training/assistant/{assistantId}', method='get')
		if req.status_code // 100 == 4:
			raise Exception(f'Snips API returned an error: {req.status_code}')
		return TrainingStatusResponse(req.json())


	def _handleTraining(self, assistantId: str):
		trainingLock = self.ThreadManager.newEvent('TrainingAssistantLock')
		trainingLock.set()
		while trainingLock.isSet():
			trainingStatus = self._trainingStatus(assistantId)

			if not trainingStatus.nluStatus.needTraining and not trainingStatus.nluStatus.inProgress and \
			   not trainingStatus.asrStatus.needTraining and not trainingStatus.asrStatus.inProgress:
				trainingLock.clear()

			elif trainingStatus.nluStatus.inProgress or trainingStatus.asrStatus.inProgress:
				pass

			elif trainingStatus.nluStatus.needTraining and \
				 not trainingStatus.nluStatus.inProgress and \
				 not trainingStatus.asrStatus.inProgress:
				self.log.info('Training NLU')
				req = self._trainAssistant(assistantId, SnipsTrainingType.NLU)
				if req.status_code == 400:
					self.log.info('There are no intents, so the assistant could not be trained')
					trainingLock.clear()
					raise Exception('Something went wrong while training the assistant')

			elif not trainingStatus.nluStatus.inProgress and \
				 trainingStatus.asrStatus.needTraining and \
				 not trainingStatus.asrStatus.inProgress:
				self.log.info('Training ASR')
				req = self._trainAssistant(assistantId, SnipsTrainingType.ASR)
				if req.status_code == 400:
					self.log.info('There are no intents, so the assistant could not be trained')
					trainingLock.clear()
					raise Exception('Something went wrong while training the assistant')

			else:
				raise Exception('Something went wrong while training the assistant')

			time.sleep(5)


	def download(self, assistantId: str) -> bool:
		try:
			self._handleTraining(assistantId)
			self.log.info('Downloading assistant...')
			req = self._req(url=f'/v3/assistant/{assistantId}/download', method='get')

			Path(tempfile.gettempdir(), 'assistant.zip').write_bytes(req.content)

			self.log.info(f'Assistant {assistantId} trained and downloaded')
			self.ThreadManager.getEvent('SnipsAssistantDownload').clear()
			return True
		except Exception as e:
			self.log.error(f'Assistant download failed: {e}')
			self.broadcast(method=constants.EVENT_SNIPS_ASSISTANT_DOWNLOAD_FAILED, exceptions=[self.name], propagateToSkills=True)
			self.ThreadManager.getEvent('SnipsAssistantDownload').cancel()
			return False


	def _logout(self):
		self._req(url=f"/v1/user/{self._user.userId}/accesstoken/{self.ConfigManager.getSnipsConfiguration('project-alice', 'console_alias')}", method='get')
		if 'Authorization' in self._headers:
			del self._headers['Authorization']
		self._connected = False

		self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_token', value='')
		self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_alias', value='')
		self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_id', value='')
		self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_email', value='')


	def login(self):
		if self._connected:
			self.log.error('SnipsConsole: cannot login, already logged in')
		else:
			self._login()


	def _req(self, url: str = '', method: str = 'post', params: dict = None, data: dict = None, **kwargs) -> requests.Response:
		"""
		Sends a http request
		:param url: the url path
		:param method: get or post
		:param params: used for method get
		:param data: used for method post
		:param kwargs:
		:return: requests.Response
		"""
		req = requests.request(method=method, url=f'https://external-gateway.snips.ai{url}', params=params, json=data, headers=self._headers, **kwargs)
		if req.status_code == 401:
			self.log.warning('Console token has expired, need to login')
			if 'Authorization' in self._headers:
				del self._headers['Authorization']
			self._connected = False

			self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_token', value='')
			self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_alias', value='')
			self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_id', value='')
			self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_email', value='')

			self._login()
		return req
