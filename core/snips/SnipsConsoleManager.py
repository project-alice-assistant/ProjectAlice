import getpass
import subprocess
from zipfile import ZipFile

import tempfile
import time
import uuid
from pathlib import Path

import requests

from core.base.SuperManager import SuperManager
from core.base.model.Manager import Manager
from core.commons import commons, constants
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

		if self.ConfigManager.getSnipsConfiguration('project-alice', 'console_token'):
			self._logger.info(f'[{self.name}] Snips console authorized')
			self._headers['Authorization'] = f"JWT {self.ConfigManager.getSnipsConfiguration('project-alice', 'console_token')}"

			self._user = SnipsConsoleUser({
				'id': self.ConfigManager.getSnipsConfiguration('project-alice', 'console_user_id'),
				'email': self.ConfigManager.getSnipsConfiguration('project-alice', 'console_user_email')
			})

			self._connected = True
		elif self.loginCredentialsAreConfigured():
			self._logger.info(f'[{self.name}] Snips console not authorized')
			self._login()
		else:
			self._logger.warning(f'[{self.name}] Snips console credentials not found')
			self.isActive = False


	def doDownload(self, modulesInfos: dict = None):
		self._logger.info(f'[{self.name}] Starting Snips assistant training and download procedure')
		self.ThreadManager.newEvent('SnipsAssistantDownload', onClearCallback='onSnipsAssistantDownloaded').set(moduleInfos=modulesInfos)
		projectId = self.LanguageManager.activeSnipsProjectId
		self.ThreadManager.newThread(name='SnipsAssistantDownload', target=self.download, args=[projectId])


	def loginCredentialsAreConfigured(self):
		return self.ConfigManager.getAliceConfigByName('snipsConsoleLogin') and \
			   self.ConfigManager.getAliceConfigByName('snipsConsolePassword')


	def _login(self):
		self._tries += 1
		if self._tries > 3:
			self._logger.info(f'- Tried to login {self._tries} times, giving up now')
			self._tries = 0
			return

		self._logger.info(f"- Connecting to Snips console using account {self.ConfigManager.getAliceConfigByName('snipsConsoleLogin')}")
		payload = {
			'email'   : self.ConfigManager.getAliceConfigByName('snipsConsoleLogin'),
			'password': self.ConfigManager.getAliceConfigByName('snipsConsolePassword')
		}

		req = self._req(url='/v1/user/auth', data=payload)
		if req.status_code == 200:
			self._logger.info(f'[{self.NAME}] Connected to Snips console. Fetching and saving access token')
			try:
				token = req.headers['authorization']
				self._user = SnipsConsoleUser(req.json()['user'])

				accessToken = self._getAccessToken(token)
				if accessToken:
					self._logger.info('- Saving console access token')
					self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_token', value=accessToken['token'])
					self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_alias', value=accessToken['alias'])
					self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_id', value=self._user.userId)
					self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_email', value=self._user.userEmail)

					self._connected = True
					self._tries = 0
				else:
					raise Exception('- Error fetching JWT console token')
			except Exception as e:
				self._logger.error(f"- Couldn't retrieve snips console token: {e}")
				self._connected = False
				return
		else:
			self._logger.error(f"- Couldn't connect to Snips console: {req.status_code}")
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
		self._req(url=f'/v2/training/assistant/{assistantId}', data={'trainingType': trainingType.value}, method='post')


	def _trainingStatus(self, assistantId: str) -> TrainingStatusResponse:
		req = self._req(url=f'/v2/training/assistant/{assistantId}', method='get')
		if req.status_code // 100 == 4:
			raise Exception(f'Snips API return a error: {req.status_code}')
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
				self._logger.info(f'[{self.name}] Training NLU')
				self._trainAssistant(assistantId, SnipsTrainingType.NLU)

			elif not trainingStatus.nluStatus.inProgress and \
				 trainingStatus.asrStatus.needTraining and \
				 not trainingStatus.asrStatus.inProgress:
				self._logger.info(f'[{self.name}] Training ASR')
				self._trainAssistant(assistantId, SnipsTrainingType.ASR)
			else:
				raise Exception(f'[{self.name}] Something went wrong while training the assistant')

			time.sleep(5)


	def download(self, assistantId: str) -> bool:
		try:
			self._handleTraining(assistantId)
			self._logger.info(f'[{self.name}] Downloading assistant...')
			req = self._req(url=f'/v3/assistant/{assistantId}/download', method='get')

			Path(tempfile.gettempdir(), 'assistant.zip').write_bytes(req.content)

			self._logger.info(f'[{self.name}] Assistant {assistantId} trained and downloaded')
			# SuperManager.getInstance().broadcast(
			# 	method='onSnipsAssistantDownloaded',
			# 	exceptions=[constants.DUMMY],
			# 	propagateToModules=True,
			# 	args=[modulesInfos]
			# )

			self.ThreadManager.getEvent('SnipsAssistantDownload').clear()
			return True
		except Exception as e:
			self._logger.error(f'[{self.name}] Assistant download failed: {e}')
			self.ModuleManager.broadcast(method='onSnipsAssistantDownloadFailed')
			self.ThreadManager.getEvent('SnipsAssistantDownload').clear()
			return False


	def _logout(self):
		self._req(url=f"/v1/user/{self._user.userId}/accesstoken/{self.ConfigManager.getSnipsConfiguration('project-alice', 'console_alias')}", method='get')
		self._headers.pop('Authorization', None)
		self._connected = False

		self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_token', value='')
		self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_alias', value='')
		self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_id', value='')
		self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_email', value='')


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
		req = requests.request(method=method, url=f'https://external-gateway.snips.ai{url}', params=params, json=data, headers=self._headers, **kwargs)
		if req.status_code == 401:
			self._logger.warning('[{}] Console token has expired, need to login')
			self._headers.pop('Authorization', None)
			self._connected = False

			self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_token', value='')
			self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_alias', value='')
			self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_id', value='')
			self.ConfigManager.updateSnipsConfiguration(parent='project-alice', key='console_user_email', value='')

			self._login()
		return req


	def onSnipsAssistantDownloaded(self, *args, **kwargs):
		try:
			filepath = Path(tempfile.gettempdir(), 'assistant.zip')
			with ZipFile(filepath) as zipfile:
				zipfile.extractall(tempfile.gettempdir())

			subprocess.run(['sudo', 'rm', '-rf', commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}'])
			subprocess.run(['sudo', 'rm', '-rf', commons.rootDir() + '/assistant'])
			subprocess.run(['sudo', 'cp', '-R', str(filepath).replace('.zip', ''), commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}'])

			time.sleep(0.5)

			subprocess.run(['sudo', 'chown', '-R', getpass.getuser(), commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}', commons.rootDir() + '/assistant'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/start_of_input.wav', commons.rootDir() + '/assistant/custom_dialogue/sound/start_of_input.wav'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/end_of_input.wav', commons.rootDir() + '/assistant/custom_dialogue/sound/end_of_input.wav'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/error.wav', commons.rootDir() + '/assistant/custom_dialogue/sound/error.wav'])

			time.sleep(0.5)

			self.SnipsServicesManager.runCmd('restart')
			SuperManager.getInstance().broadcast(
				method='onSnipsAssistantInstalled',
				exceptions=[constants.DUMMY],
				propagateToModules=True
			)
		except Exception as e:
			self._logger.error(f'[{self.name}] Failed installing Snips Assistant: {e}')
			SuperManager.getInstance().broadcast(
				method='onSnipsAssistantFailedInstalling',
				exceptions=[constants.DUMMY],
				propagateToModules=True
			)