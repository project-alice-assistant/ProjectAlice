import subprocess

from flask import render_template, request, jsonify

from core.interface.views.View import View


class AdminView(View):
	excluded_methods = ['isfloat']
	route_base = '/admin/'
	waitType = ''

	def index(self):
		return render_template('admin.html',
		                       langData=self._langData,
		                       devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'),
		                       updateChannel=self.ConfigManager.getAliceConfigByName('updateChannel'),
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	@classmethod
	def setWaitType(cls, value: str):
		cls.waitType = value


	@classmethod
	def getWaitType(cls) -> str:
		return cls.waitType


	def saveAliceSettings(self):
		try:
			# Create the conf dict. on and off values are translated to True and False and we try to cast to int
			# because HTTP data is type less.
			confs = {key: False if value == 'off' else True if value == 'on' else int(value) if value.isdigit() else float(value) if self.isfloat(value) else value for key, value in request.form.items()}

			confs['modules'] = self.ConfigManager.getAliceConfigByName('modules')
			confs['supportedLanguages'] = self.ConfigManager.getAliceConfigByName('supportedLanguages')

			self.ConfigManager.writeToAliceConfigurationFile(confs=confs)
			return self.index()
		except Exception as e:
			self.logError(f'Failed saving Alice config: {e}')
			return self.index()


	def restart(self) -> dict:
		try:
			self.__class__.setWaitType('restart')
			self.ThreadManager.doLater(interval=2, func=self.ProjectAlice.doRestart)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed restarting Alice: {e}')
			return jsonify(success=False)


	def reboot(self) -> dict:
		try:
			self.__class__.setWaitType('reboot')
			self.ProjectAlice.onStop()
			self.ThreadManager.doLater(interval=2, func=subprocess.run, args=[['sudo', 'shutdown', '-r', 'now']])
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed rebooting device: {e}')
			return jsonify(success=False)


	def assistantDownload(self) -> dict:
		try:
			self.__class__.setWaitType('snipsdownload')
			self.SnipsConsoleManager.doDownload()
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed downloading assistant: {e}')
			return jsonify(success=False)


	def areYouReady(self) -> bool:
		if not self.__class__.getWaitType() or self.__class__.getWaitType() in ['restart', 'reboot']:
			return jsonify(success=False) if self.ProjectAlice.restart else jsonify(success=True)
		elif self.__class__.getWaitType() == 'snipsdownload':
			return jsonify(success=False) if self.ThreadManager.getEvent('SnipsAssistantDownload').isSet() else jsonify(success=True)
		else:
			return False


	# noinspection PyMethodMayBeStatic
	def isfloat(self, value: str) -> bool:
		try:
			value = float(value)
			return True
		except:
			return False
