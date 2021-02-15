from flask import jsonify, request, send_from_directory
from flask_classful import route

from core.ProjectAliceExceptions import ConfigurationUpdateFailed
from core.commons import constants
from core.webApi.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class UtilsApi(Api):
	route_base = f'/api/{Api.version()}/utils/'


	def __init__(self):
		super().__init__()


	@route('/restart/')
	@ApiAuthenticated
	def restart(self):
		try:
			self.ThreadManager.doLater(interval=2, func=self.ProjectAlice.doRestart)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed restarting Alice: {e}')
			return jsonify(success=False, message=str(e))


	@route('/reboot/')
	@ApiAuthenticated
	def reboot(self):
		try:
			self.ThreadManager.doLater(interval=2, func=self.Commons.runRootSystemCommand, args=[['shutdown', '-r', 'now']])
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed rebooting device: {e}')
			return jsonify(success=False, message=str(e))


	@route('/update/')
	@ApiAuthenticated
	def update(self):
		try:
			self.ProjectAlice.updateProjectAlice()
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed updating Alice: {e}')
			return jsonify(success=False, message=str(e))


	@route('/config/', methods=['GET'])
	def config(self):
		"""
		Returns Alice configs. If authenticated, with passwords, if not, sensitive data is removed
		"""
		try:
			configs = self.ConfigManager.aliceConfigurations
			configs['aliceIp'] = self.Commons.getLocalIp()
			configs['apiPort'] = self.ConfigManager.getAliceConfigByName('apiPort')
			configs['aliceVersion'] = constants.VERSION
			if not self.UserManager.apiTokenValid(request.headers.get('auth', '') or self.UserManager.apiTokenLevel(request.headers.get('auth')) != 'admin'):
				configs = {key: value for key, value in configs.items() if not self.ConfigManager.isAliceConfSensitive(key)}

			return jsonify(success=True, config=configs, templates=self.ConfigManager.aliceTemplateConfigurations, categories=self.ConfigManager.aliceConfigurationCategories)
		except Exception as e:
			self.logError(f'Failed retrieving Alice configs: {e}')
			return jsonify(success=False, message=str(e))


	@route('/config/', methods=['PATCH'])
	def setConfig(self):
		try:
			confs = request.json
			confs.pop('aliceIp', None)
			confs.pop('apiPort', None)
			confs.pop('aliceVersion', None)
			for conf, value in confs.items():
				if value == self.ConfigManager.getAliceConfigByName(conf):
					continue

				try:
					self.ConfigManager.updateAliceConfiguration(conf, value, False)
				except ConfigurationUpdateFailed as e:
					self.logError(f'Updating config failed for **{conf}**: {e}')

			self.ConfigManager.writeToAliceConfigurationFile()

			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed saving Alice configs: {e}')
			return jsonify(success=False, message=str(e))


	@route('/mqttConfig/', methods=['GET'])
	def mqttConfig(self):
		mqttHost = self.ConfigManager.getAliceConfigByName('mqttHost')

		if mqttHost == 'localhost' or mqttHost == '127.0.0.1':
			mqttHost = self.Commons.getLocalIp()

		return jsonify(
			success=True,
			host=mqttHost,
			port=int(self.ConfigManager.getAliceConfigByName('mqttPort')) + 1
		)


	@route('/i18n/', methods=['GET'])
	def i18n(self):
		return jsonify(success=True, data=self.LanguageManager.loadWebUIStrings())


	@route('/i18n/<lang>/', methods=['GET'])
	def i18nLang(self, lang: str):
		return jsonify(success=True, data=self.LanguageManager.loadWebUIStrings().get(lang, dict()))


	@route('/sysCmd/', methods=['POST'])
	def sysCmd(self):
		cmd = request.form.get('cmd', '')
		cmd = cmd.split() if ' ' in cmd else [cmd]

		if self.UserManager.apiTokenValid(request.headers.get('auth', '')):
			self.Commons.runRootSystemCommand(cmd)
		else:
			self.Commons.runSystemCommand(cmd)

		return jsonify(success=True)


	@ApiAuthenticated
	def addWakeword(self) -> dict:
		try:
			self.SkillManager.getSkillInstance('AliceCore').addNewWakeword()
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed adding new wakeword: {e}')
			return jsonify(success=False, message=str(e))


	@ApiAuthenticated
	def tuneWakeword(self) -> dict:
		try:
			self.SkillManager.getSkillInstance('AliceCore').tuneWakeword()
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed tuning wakeword: {e}')
			return jsonify(success=False, message=str(e))


	@ApiAuthenticated
	def wipeAll(self) -> dict:
		try:
			self.ProjectAlice.wipeAll()
			self.ThreadManager.doLater(interval=2, func=self.ProjectAlice.doRestart)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed wiping system: {e}')
			return jsonify(success=False, message=str(e))


	@ApiAuthenticated
	def addUser(self) -> dict:
		try:
			uid = request.headers.get('uid', '')
			if not uid:
				raise Exception('No device uid defined')

			session = self.DialogManager.newSession(deviceUid=uid)
			self.SkillManager.getSkillInstance('AliceCore').addNewUser(session=session)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed adding new user: {e}')
			return jsonify(success=False, message=str(e))


	@ApiAuthenticated
	def train(self) -> dict:
		try:
			self.AssistantManager.checkAssistant(forceRetrain=True)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed training assistant: {e}')
			return jsonify(success=False, message=str(e))


	def pahows(self) -> dict:
		try:
			return send_from_directory(f'{self.Commons.rootDir()}/core/webApi/static', 'pahows.js')
		except Exception as e:
			self.logError(f'Error fetching pahows.js {e}')
			return jsonify(success=False, message=str(e))


	def Widget(self) -> dict:
		try:
			return send_from_directory(f'{self.Commons.rootDir()}/core/webApi/static', 'Widget.js')
		except Exception as e:
			self.logError(f'Error fetching Widget.js {e}')
			return jsonify(success=False, message=str(e))
