import json
import time
import uuid

from pathlib import Path
import requests
import tempfile

from core.base.model.Manager import Manager
from core.base.SuperManager import SuperManager
from core.snips.model.SnipsConsoleUser import SnipsConsoleUser
from core.snips.model.SnipsTrainingStatus import SnipsTrainingType, TrainingStatusResponse


class SnipsConsoleManager(Manager):

	NAME = 'SnipsConsoleManager'

	def __init__(self):
		super().__init__(self.NAME)

		self._connected     = False
		self._tries         = 0
		self._user          = None

		self._headers       = {
			'Accept'    	: 'application/json',
			'Content-Type' 	: 'application/json'
		}


	def onStart(self):
		super().onStart()

		if SuperManager.getInstance().configManager.getSnipsConfiguration('project-alice', 'console_token'):
			self._logger.info('[{}] Snips console authorized'.format(self.name))
			self._headers['Authorization'] = 'JWT {}'.format(SuperManager.getInstance().configManager.getSnipsConfiguration('project-alice', 'console_token'))

			self._user = SnipsConsoleUser({
				'id': SuperManager.getInstance().configManager.getSnipsConfiguration('project-alice', 'console_user_id'),
				'email': SuperManager.getInstance().configManager.getSnipsConfiguration('project-alice', 'console_user_email')
			})

			self._connected = True
		elif self.loginCredentialsAreConfigured():
			self._logger.info('[{}] Snips console not authorized'.format(self.name))
			self._login()
		else:
			self._logger.warning('[{}] Snips console credentials not found'.format(self.name))
			self.isActive = False


	def doDownload(self):
		self._logger.info('[{}] Starting Snips assistant training and download procedure'.format(self.name))
		SuperManager.getInstance().threadManager.newLock('SnipsAssistantDownload').set()
		projectId = SuperManager.getInstance().languageManager.activeSnipsProjectId
		SuperManager.getInstance().threadManager.newThread(name='SnipsAssistantDownload', target=self.download, args=[projectId])


	@staticmethod
	def loginCredentialsAreConfigured():
		return SuperManager.getInstance().configManager.getAliceConfigByName('snipsConsoleLogin') and \
			   SuperManager.getInstance().configManager.getAliceConfigByName('snipsConsolePassword')


	def _login(self):
		self._tries += 1
		if self._tries > 3:
			self._logger.info('- Tried to login {} times, giving up now'.format(self._tries))
			self._tries = 0
			return

		self._logger.info('- Connecting to Snips console using account {}'.format(SuperManager.getInstance().configManager.getAliceConfigByName('snipsConsoleLogin')))
		payload = {
			'email'   : SuperManager.getInstance().configManager.getAliceConfigByName('snipsConsoleLogin'),
			'password': SuperManager.getInstance().configManager.getAliceConfigByName('snipsConsolePassword')
		}

		req = self._req(url='/v1/user/auth', data=payload)
		if req.status_code == 200:
			self._logger.info('[{}] Connected to Snips console. Fetching and saving access token'.format(self.NAME))
			try:
				token = req.headers['authorization']
				self._user = SnipsConsoleUser(json.loads(req.content)['user'])

				accessToken = self._getAccessToken(token)
				if accessToken:
					self._logger.info('- Saving console access token')
					SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_token', value=accessToken['token'])
					SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_alias', value=accessToken['alias'])
					SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_user_id', value=self._user.userId)
					SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_user_email', value=self._user.userEmail)

					self._connected = True
					self._tries = 0
				else:
					raise Exception('- Error fetching JWT console token')
			except Exception as e:
				self._logger.error("- Couldn't retrieve snips console token: {}".format(e))
				self._connected = False
				return
		else:
			self._logger.error("- Couldn't connect to Snips console: {}".format(req.status_code))
			self._connected = False


	def _getAccessToken(self, token: str) -> dict:
		alias = 'projectalice-{}'.format(uuid.uuid4()).replace('-', '')[:29]
		self._headers['Authorization'] = token
		req = self._req(url='/v1/user/{}/accesstoken'.format(self._user.userId), data={'alias': alias})
		if req.status_code == 201:
			return json.loads(req.content)['token']
		return dict()


	def _listAssistants(self) -> dict:
		req = self._req(url='/v3/assistant', method='get', data={'userId': self._user.userId})
		return json.loads(req.content)['assistants']


	def _trainAssistant(self, assistantId: str, trainingType: SnipsTrainingType):
		self._req(url='/v2/training/assistant/{}'.format(assistantId), data={'trainingType': trainingType.value}, method='post')


	def _trainingStatus(self, assistantId: str) -> TrainingStatusResponse:
		req = self._req(url='/v2/training/assistant/{}'.format(assistantId), method='get')
		return TrainingStatusResponse(json.loads(req.content.decode()))


	def _handleTraining(self, assistantId: str):
		trainingLock = SuperManager.getInstance().threadManager.newLock('TrainingAssistantLock')
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
				self._logger.info('[{}] Training NLU'.format(self.name))
				self._trainAssistant(assistantId, SnipsTrainingType.NLU)

			elif not trainingStatus.nluStatus.inProgress and \
				 trainingStatus.asrStatus.needTraining and \
				 not trainingStatus.asrStatus.inProgress:
				self._logger.info('[{}] Training ASR'.format(self.name))
				self._trainAssistant(assistantId, SnipsTrainingType.ASR)
			else:
				raise Exception('[{}] Something went wrong while training the assistant'.format(self.name))

			time.sleep(5)


	def download(self, assistantId: str):
		try:
			self._handleTraining(assistantId)
			self._logger.info('[{}] Downloading assistant...'.format(self.name))
			req = self._req(url='/v3/assistant/{}/download'.format(assistantId), method='get')

			Path(tempfile.gettempdir(), 'assistant.zip').write_bytes(req.content)

			self._logger.info('[{}] Assistant {} trained and downloaded'.format(self.name, assistantId))
			SuperManager.getInstance().moduleManager.broadcast(method='onSnipsAssistantDownloaded')
		except Exception as e:
			self._logger.error('[{}] Assistant download failed: {}'.format(self.name, e))
			SuperManager.getInstance().moduleManager.broadcast(method='onSnipsAssistantDownloadFailed')
		finally:
			SuperManager.getInstance().threadManager.getLock('SnipsAssistantDownload').clear()


	def _logout(self):
		self._req(url='/v1/user/{}/accesstoken/{}'.format(self._user.userId, SuperManager.getInstance().configManager.getSnipsConfiguration('project-alice', 'console_alias')), method='get')
		self._headers.pop('Authorization', None)
		self._connected = False

		SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_token', value='')
		SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_alias', value='')
		SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_user_id', value='')
		SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_user_email', value='')


	def login(self):
		if self._connected:
			self._logger.error('SnipsConsole: cannot login, already logged in')
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
		req = requests.request(method=method, url='https://external-gateway.snips.ai{}'.format(url), params=params, json=data, headers=self._headers, **kwargs)
		if req.status_code == 401:
			self._logger.warning('[{}] Console token has expired, need to login'.format(self.name))
			self._headers.pop('Authorization', None)
			self._connected = False

			SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_token', value='')
			SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_alias', value='')
			SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_user_id', value='')
			SuperManager.getInstance().configManager.updateSnipsConfiguration(parent='project-alice', key='console_user_email', value='')

			self._login()
		return req
