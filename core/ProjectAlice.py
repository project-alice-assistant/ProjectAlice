import hashlib
import subprocess
from pathlib import Path

import requests

from core.base.SuperManager import SuperManager
from core.base.model.StateType import StateType
from core.base.model.Version import Version
from core.commons import constants
from core.commons.model.Singleton import Singleton
from core.util.Stopwatch import Stopwatch
from core.util.model.Logger import Logger
from core.webui.model.UINotificationType import UINotificationType


class ProjectAlice(Singleton):
	NAME = 'ProjectAlice'


	def __init__(self, restartHandler: callable):
		Singleton.__init__(self, self.NAME)
		self._logger = Logger(prepend='[Project Alice]')
		self._logger.logInfo('Starting Alice main unit')
		self._booted = False
		self._isUpdating = False
		self._shuttingDown = False
		self._restart = False
		self._restartHandler = restartHandler

		if not self.checkDependencies():
			self._restart = True
			self._restartHandler()
		else:
			with Stopwatch() as stopWatch:
				self._superManager = SuperManager(self)

				self._superManager.initManagers()
				self._superManager.onStart()

				if self._superManager.configManager.getAliceConfigByName('useHLC'):
					self._superManager.commons.runRootSystemCommand(['systemctl', 'start', 'hermesledcontrol'])

				self._superManager.onBooted()

			self._logger.logInfo(f'Started in {stopWatch} seconds')
			self._booted = True


	def checkDependencies(self) -> bool:
		"""
		Compares .hash files against requirements.txt and sysrrequirement.txt. Updates dependencies if necessary
		:return: boolean False if the check failed, new deps were installed (reboot maybe? :) )
		"""
		HASH_SUFFIX = '.hash'
		TXT_SUFFIX = '.txt'

		path = Path('requirements')
		savedHash = path.with_suffix(HASH_SUFFIX)
		reqHash = hashlib.blake2b(path.with_suffix(TXT_SUFFIX).read_bytes()).hexdigest()

		if not savedHash.exists() or savedHash.read_text() != reqHash:
			self._logger.logInfo('Pip dependencies added or removed, updating virtual environment')
			subprocess.run(['./venv/bin/pip', 'install', '-r', str(path.with_suffix(TXT_SUFFIX))])
			savedHash.write_text(reqHash)
			return False

		path = Path('sysrequirements')
		savedHash = path.with_suffix(HASH_SUFFIX)
		reqHash = hashlib.blake2b(path.with_suffix(TXT_SUFFIX).read_bytes()).hexdigest()

		if not savedHash.exists() or savedHash.read_text() != reqHash:
			self._logger.logInfo('System dependencies added or removed, updating system')
			reqs = [line.rstrip('\n') for line in open(path.with_suffix(TXT_SUFFIX))]
			subprocess.run(['sudo', 'apt-get', 'install', '-y', '--allow-unauthenticated'] + reqs)
			savedHash.write_text(reqHash)
			return False

		path = Path('pipuninstalls')
		savedHash = path.with_suffix(HASH_SUFFIX)
		reqHash = hashlib.blake2b(path.with_suffix(TXT_SUFFIX).read_bytes()).hexdigest()

		if not savedHash.exists() or savedHash.read_text() != reqHash:
			self._logger.logInfo('Pip conflicting dependencies added, updating virtual environment')
			subprocess.run(['./venv/bin/pip', 'uninstall', '-y', '-r', str(path.with_suffix(TXT_SUFFIX))])
			savedHash.write_text(reqHash)
			return False

		return True


	@property
	def name(self) -> str: #NOSONAR
		return self.NAME


	@property
	def isBooted(self) -> bool:
		return self._booted


	@property
	def restart(self) -> bool:
		return self._restart


	@restart.setter
	def restart(self, value: bool):
		self._restart = value


	def doRestart(self):
		self._restart = True
		self.onStop()


	def onStop(self, withReboot: bool = False):
		self._logger.logInfo('Shutting down')
		self._shuttingDown = True
		self._superManager.onStop()
		if self._superManager.configManager.getAliceConfigByName('useHLC'):
			self._superManager.commons.runRootSystemCommand(['systemctl', 'stop', 'hermesledcontrol'])

		self._booted = False
		self.INSTANCE = None

		if withReboot:
			subprocess.run(['sudo', 'shutdown', '-r', 'now'])
		else:
			self._restartHandler()


	def wipeAll(self):
		# Set as restarting so skills don't install / update
		self._restart = True

		self._superManager.skillManager.wipeSkills()
		self._superManager.databaseManager.clearDB()
		self._superManager.assistantManager.clearAssistant()
		self._superManager.dialogTemplateManager.clearCache(False)
		self._superManager.nluManager.clearCache()


	def updateProjectAlice(self):
		self._logger.logInfo('Checking for core updates')
		STATE = 'projectalice.core.updating'
		state = self._superManager.stateManager.getState(STATE)
		if not state:
			self._superManager.stateManager.register(STATE, initialState=StateType.RUNNING)
		elif state.currentState == StateType.RUNNING:
			self._logger.logInfo('Update cancelled, already running')
			return

		self._superManager.stateManager.setState(STATE, newState=StateType.RUNNING)

		self._isUpdating = True
		req = requests.get(url=f'{constants.GITHUB_API_URL}/ProjectAlice/branches', auth=SuperManager.getInstance().configManager.getGithubAuth())
		if req.status_code != 200:
			self._logger.logWarning('Failed checking for updates')
			self._superManager.stateManager.setState(STATE, newState=StateType.ERROR)
			return

		userUpdatePref = SuperManager.getInstance().configManager.getAliceConfigByName('aliceUpdateChannel')

		if userUpdatePref == 'master':
			candidate = 'master'
		else:
			candidate = Version.fromString(constants.VERSION)
			for branch in req.json():
				repoVersion = Version.fromString(branch['name'])
				if not repoVersion.isVersionNumber:
					continue

				releaseType = repoVersion.releaseType
				if userUpdatePref == 'rc' and releaseType in {'b', 'a'} or userUpdatePref == 'beta' and releaseType == 'a':
					continue

				if repoVersion > candidate:
					candidate = repoVersion

		self._logger.logInfo(f'Checking on "{str(candidate)}" update channel')
		commons = SuperManager.getInstance().commons

		currentHash = subprocess.check_output(['git', 'rev-parse', '--short HEAD'])

		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'stash'])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'clean', '-df'])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'checkout', str(candidate)])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'pull'])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'submodule', 'init'])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'submodule', 'update'])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'submodule', 'foreach', 'git', 'checkout', f'builds_{str(candidate)}'])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'submodule', 'foreach', 'git', 'pull'])

		newHash = subprocess.check_output(['git', 'rev-parse', '--short HEAD'])

		# Remove install tickets
		[file.unlink() for file in Path(commons.rootDir(), 'system/skillInstallTickets').glob('*') if file.is_file()]

		self._superManager.stateManager.setState(STATE, newState=StateType.FINISHED)

		if currentHash != newHash:
			self._logger.logWarning('New Alice version installed, need to restart...')

			self._superManager.webUiManager.newNotification(
				tipe=UINotificationType.INFO,
				title=self._superManager.languageManager.getString('aliceUpdatedTitle'),
				text=self._superManager.languageManager.getString('aliceUpdatedText')
			)
			self.doRestart()

		self._logger.logInfo('Update checks completed.')
		self._isUpdating = False


	@property
	def updating(self) -> bool:
		return self._isUpdating


	@property
	def shuttingDown(self) -> bool:
		return self._shuttingDown
