from typing import Any

from flask import jsonify, render_template, request
from flask_login import login_required

from core.interface.model.View import View


class AdminView(View):
	excluded_methods = ['isfloat']
	route_base = '/admin/'
	waitType = ''


	@login_required
	def index(self):
		return render_template(template_name_or_list='admin.html',
		                       langData=self._langData,
		                       aliceSettingCategories=self.ConfigManager.aliceConfigurationCategories,
		                       aliceSettings=self.ConfigManager.aliceConfigurations,
		                       aliceSettingsTemplate=self.ConfigManager.aliceTemplateConfigurations)


	@classmethod
	def setWaitType(cls, value: str):
		cls.waitType = value


	@classmethod
	def getWaitType(cls) -> str:
		return cls.waitType


	def saveAliceSettings(self):
		try:
			# Create the conf dict. on and off values are translated to True and False and we try to cast to int
			# or float because HTTP data is type less.
			confs = {key: self.retrieveValue(value) for key, value in request.form.items()}

			postProcessing = set()
			for conf, value in confs.items():
				if value == self.ConfigManager.getAliceConfigByName(conf):
					continue

				pre = self.ConfigManager.getAliceConfUpdatePreProcessing(conf)
				if pre and not self.ConfigManager.doConfigUpdatePreProcessing(pre, value):
					continue

				pp = self.ConfigManager.getAliceConfUpdatePostProcessing(conf)
				if pp:
					postProcessing.add(pp)

			confs['supportedLanguages'] = self.ConfigManager.getAliceConfigByName('supportedLanguages')

			self.ConfigManager.writeToAliceConfigurationFile(confs=confs)
			self.ConfigManager.doConfigUpdatePostProcessing(postProcessing)
			return self.index()
		except Exception as e:
			self.logError(f'Failed saving Alice config: {e}')
			return self.index()


	def restart(self) -> dict:
		try:
			self.__class__.setWaitType('restart')
			self.ThreadManager.doLater(interval=1, func=self.ProjectAlice.doRestart)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed restarting Alice: {e}')
			return jsonify(success=False)


	def reboot(self) -> dict:
		try:
			self.__class__.setWaitType('reboot')
			self.ProjectAlice.onStop(withReboot=True)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed rebooting device: {e}')
			return jsonify(success=False)


	def trainAssistant(self) -> dict:
		try:
			self.__class__.setWaitType('trainAssistant')
			self.ThreadManager.newEvent('TrainAssistant').set()
			self.AssistantManager.checkAssistant(forceRetrain=True)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed training assistant: {e}')
			return jsonify(success=False)


	def updatee(self) -> dict:
		try:
			self.__class__.setWaitType('update')
			self.ProjectAlice.updateProjectAlice()
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed updating Project Alice: {e}')
			return jsonify(success=False)


	def addUser(self) -> dict:
		try:
			self.SkillManager.getSkillInstance('AliceCore').addNewUser()
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed adding new user: {e}')
			return jsonify(success=False)


	def addWakeword(self) -> dict:
		try:
			self.SkillManager.getSkillInstance('AliceCore').addNewWakeword()
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed adding new wakeword: {e}')
			return jsonify(success=False)


	def tuneWakeword(self) -> dict:
		try:
			self.SkillManager.getSkillInstance('AliceCore').tuneWakeword()
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed tuning wakeword: {e}')
			return jsonify(success=False)


	def wipeAll(self) -> dict:
		try:
			self.ProjectAlice.wipeAll()
			return self.restart()
		except Exception as e:
			self.logError(f'Failed wiping system: {e}')
			return jsonify(success=False)


	def areYouReady(self) -> bool:
		if not self.__class__.getWaitType() or self.__class__.getWaitType() in ['restart', 'reboot']:
			return jsonify(success=False) if self.ProjectAlice.restart else jsonify(success=True)
		elif self.__class__.getWaitType() == 'trainAssistant':
			return jsonify(success=False) if self.ThreadManager.getEvent('TrainAssistant').isSet() else jsonify(success=True)
		else:
			return jsonify(success=False)


	@classmethod
	def retrieveValue(cls, value: str) -> Any:
		if value == 'off':
			return False
		if value == 'on':
			return True
		if value.isdigit():
			return int(value)
		if cls.isfloat(value):
			return float(value)
		return value


	@staticmethod
	def isfloat(value: str) -> bool:
		try:
			_ = float(value)
			return True
		except:
			return False
