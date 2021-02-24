from flask import jsonify, request
from flask_classful import route

from core.webApi.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class SkillsApi(Api):
	route_base = f'/api/{Api.version()}/skills/'


	@route('/')
	def index(self):
		return jsonify(skills={skillName: skill.toDict() for skillName, skill in self.SkillManager.allSkills.items()})


	# noinspection PyMethodMayBeStatic
	def skillNotFound(self):
		return jsonify(success=False, reason='skill not found')


	@ApiAuthenticated
	def delete(self, skillName: str):
		if skillName in self.SkillManager.neededSkills:
			return jsonify(success=False, reason='skill cannot be deleted')

		try:
			self.SkillManager.removeSkill(skillName)
			return jsonify(success=True)
		except Exception as e:
			return jsonify(success=False, reason=f'Failed deleting skill: {e}')


	@route('/getStore/')
	def getStore(self):
		return jsonify(store=self.SkillStoreManager.getStoreData())


	@ApiAuthenticated
	@route('/createSkill/', methods=['PUT'])
	def createSkill(self):
		try:
			newSkill = {
				'name'                  : request.form.get('skillName', ''),
				'speakableName'         : request.form.get('skillSpeakableName', ''),
				'description'           : request.form.get('skillDescription', 'Missing description'),
				'category'              : request.form.get('skillCategory', 'undefined'),
				'fr'                    : request.form.get('fr', False),
				'de'                    : request.form.get('de', False),
				'it'                    : request.form.get('it', False),
				'pl'                    : request.form.get('pl', False),
				'instructions'          : request.form.get('skillInstructions', False),
				'pipreq'                : request.form.get('skillPipRequirements', ''),
				'sysreq'                : request.form.get('skillSystemRequirements', ''),
				'conditionOnline'       : request.form.get('skillOnline', False),
				'conditionASRArbitrary' : request.form.get('skillArbitrary', False),
				'conditionSkill'        : request.form.get('skillRequiredSkills', ''),
				'conditionNotSkill'     : request.form.get('skillConflictingSkills', ''),
				'conditionActiveManager': request.form.get('skillRequiredManagers', ''),
				'widgets'               : request.form.get('skillWidgets', ''),
				'nodes'                 : request.form.get('skillScenarioNodes', ''),
				'devices'               : request.form.get('devices', '')
			}

			if not self.SkillManager.createNewSkill(newSkill):
				raise Exception

			return jsonify(success=True)

		except Exception as e:
			self.logError(f'Something went wrong creating a new skill: {e}')
			return jsonify(success=False, message=str(e))


	@ApiAuthenticated
	@route('/uploadSkill/', methods=['POST'])
	def uploadToGithub(self):
		try:
			skillName = request.form.get('skillName', '')
			skillDesc = request.form.get('skillDesc', '')

			if not skillName:
				raise Exception('Missing skill name')

			if self.SkillManager.uploadSkillToGithub(skillName, skillDesc):
				return jsonify(success=True, url=f'https://github.com/{self.ConfigManager.getAliceConfigByName("githubUsername")}/skill_{skillName}.git')

			return jsonify(success=False, message=f'Error while uploading to github!')
		except Exception as e:
			self.logError(f'Failed uploading to github: {e}')
			return jsonify(success=False, message=str(e))


	@ApiAuthenticated
	@route('/installSkills/', methods=['PUT'])
	def installSkills(self):
		try:
			skills = request.json

			status = dict()
			for skill in skills:
				if self.SkillManager.downloadInstallTicket(skill):
					status[skill] = 'ok'
				else:
					status[skill] = 'ko'

			return jsonify(success=True, status=status)
		except Exception as e:
			self.logWarning(f'Failed installing skill: {e}', printStack=True)
			return jsonify(success=False, message=str(e))


	@route('/<skillName>/', methods=['PATCH'])
	@ApiAuthenticated
	def saveSkillSettings(self, skillName: str):
		try:
			for confName, confValue in request.json.items():
				self.ConfigManager.updateSkillConfigurationFile(
					skillName=skillName,
					key=confName,
					value=confValue
				)

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f'Failed updating skill settings: {e}', printStack=True)
			return jsonify(success=False, message=str(e))


	@route('/<skillName>/')
	@ApiAuthenticated
	def get(self, skillName: str):
		try:
			skill = self.SkillManager.getSkillInstance(skillName=skillName, silent=True)
			if not skill:
				skill = self.SkillManager.allSkills.get(skillName, dict())
			return jsonify(success=True, skill=skill.toDict())
		except Exception as e:
			self.logWarning(f'Failed fetching skill: {e}', printStack=True)
			return jsonify(success=False, message=str(e))


	@route('/<skillName>/toggleActiveState/')
	@ApiAuthenticated
	def toggleActiveState(self, skillName: str):
		try:
			if skillName not in self.SkillManager.allSkills:
				return self.skillNotFound()

			if self.SkillManager.isSkillActive(skillName):
				if skillName in self.SkillManager.neededSkills:
					return jsonify(success=False, message='Required skill cannot be deactivated!')

				self.SkillManager.deactivateSkill(skillName=skillName, persistent=True)
			else:
				self.SkillManager.activateSkill(skillName=skillName, persistent=True)

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f'Failed toggling skill: {e}', printStack=True)
			return jsonify(success=False, message=str(e))


	@route('/<skillName>/activate/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def activate(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		if self.SkillManager.isSkillActive(skillName):
			return jsonify(success=False, reason='already active')
		else:
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.SkillManager.activateSkill(skillName=skillName, persistent=persistent)
			return jsonify(success=True)


	@route('/<skillName>/deactivate/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def deactivate(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		if skillName in self.SkillManager.neededSkills:
			return jsonify(success=False, reason='skill cannot be deactivated')

		if self.SkillManager.isSkillActive(skillName):
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.SkillManager.deactivateSkill(skillName=skillName, persistent=persistent)
			return jsonify(success=True)
		else:
			return jsonify(success=False, reason='not active')


	@route('/<skillName>/reload/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def reload(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		try:
			self.logInfo(f'Reloading skill "{skillName}"')
			self.SkillManager.reloadSkill(skillName)
			skill = self.SkillManager.getSkillInstance(skillName=skillName, silent=True)
			return jsonify(skill=skill.toDict() if skill else dict())
		except Exception as e:
			self.logWarning(f'Failed reloading skill: {e}', printStack=True)
			return jsonify(success=False, message=str(e))


	@ApiAuthenticated
	def put(self, skillName: str):
		if not self.SkillStoreManager.skillExists(skillName):
			return self.skillNotFound()
		elif self.SkillManager.getSkillInstance(skillName, True) is not None:
			return jsonify(success=False, reason='skill already installed')

		try:
			if not self.SkillManager.downloadInstallTicket(skillName):
				return jsonify(success=False, reason='skill not found')
		except Exception as e:
			self.logWarning(f'Failed installing skill: {e}', printStack=True)
			return jsonify(success=False, message=str(e))

		return jsonify(success=True)


	@route('/<skillName>/checkUpdate/')
	@ApiAuthenticated
	def checkUpdate(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		return jsonify(success=self.SkillManager.checkForSkillUpdates(skillToCheck=skillName))
