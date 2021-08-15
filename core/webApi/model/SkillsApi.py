#  Copyright (c) 2021
#
#  This file, SkillsApi.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.07.28 at 17:43:12 CEST


import json
from flask import jsonify, request
from flask_classful import route
from pathlib import Path

from core.base.model.GithubCloner import GithubCloner
from core.commons import constants
from core.util.Decorators import ApiAuthenticated
from core.webApi.model.Api import Api


class SkillsApi(Api):
	route_base = f'/api/{Api.version()}/skills/'


	@route('/')
	def index(self):
		return jsonify(skills={skillName: skill.toDict() for skillName, skill in self.SkillManager.allSkills.items()})


	# noinspection PyMethodMayBeStatic
	def skillNotFound(self):
		return jsonify(success=False, reason='skill not found')


	# noinspection PyMethodMayBeStatic
	def githubMissing(self):
		return jsonify(success=False, reason='github auth not found')


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
				'name'                  : request.form.get('name', ''),
				'speakableName'         : request.form.get('speakableName', ''),
				'description'           : request.form.get('description', 'Missing description'),
				'category'              : request.form.get('category', 'undefined'),
				'fr'                    : request.form.get('french', False),
				'de'                    : request.form.get('german', False),
				'it'                    : request.form.get('italian', False),
				'pl'                    : request.form.get('polish', False),
				'instructions'          : request.form.get('instructions', False),
				'pipreq'                : request.form.get('pipreq', ''),
				'sysreq'                : request.form.get('sysreq', ''),
				'conditionOnline'       : request.form.get('conditionOnline', False),
				'conditionASRArbitrary' : request.form.get('conditionASRArbitrary', False),
				'conditionSkill'        : request.form.get('conditionSkill', ''),
				'conditionNotSkill'     : request.form.get('conditionNotSkill', ''),
				'conditionActiveManager': request.form.get('conditionActiveManager', ''),
				'widgets'               : request.form.get('widgets', ''),
				'nodes'                 : request.form.get('nodes', ''),
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


	@route('/<skillName>/setModified/')
	@ApiAuthenticated
	def setModified(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		if not GithubCloner.hasAuth():
			return self.githubMissing()

		gitCloner = GithubCloner(baseUrl=f'{constants.GITHUB_URL}/skill_{skillName}.git', dest=Path(self.Commons.rootDir()) / 'skills' / skillName)
		self.SkillManager.getSkillInstance(skillName=skillName).modified = True
		if not gitCloner.checkOwnRepoAvailable(skillName=skillName):
			self.SkillManager.createForkForSkill(skillName=skillName)
		gitCloner.checkoutOwnFork(skillName=skillName)
		return jsonify(success=True)


	@route('/<skillName>/revert/')
	@ApiAuthenticated
	def revert(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()
		self.SkillManager.getSkillInstance(skillName=skillName).modified = False
		gitCloner = GithubCloner(baseUrl=f'{constants.GITHUB_URL}/skill_{skillName}.git', dest=Path(self.Commons.rootDir()) / 'skills' / skillName)
		gitCloner.checkoutMaster()
		return self.checkUpdate(skillName)


	@route('/<skillName>/upload/')
	@ApiAuthenticated
	def upload(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()
		self.SkillManager.getSkillInstance(skillName=skillName).modified = False
		gitCloner = GithubCloner(baseUrl=f'{constants.GITHUB_URL}/skill_{skillName}.git', dest=Path(self.Commons.rootDir()) / 'skills' / skillName)
		gitCloner.gitPush()
		return jsonify(success=True)


	@route('/<skillName>/getInstructions/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def getInstructions(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		instructionsFile = skill.getResource(f'instructions/{data["lang"]}.md')
		if not instructionsFile.exists():
			instructionsFile = skill.getResource(f'instructions/en.md')

		return jsonify(success=True, instruction=instructionsFile.read_text() if instructionsFile.exists() else '')


	@route('/<skillName>/setInstructions/', methods=['PATCH'])
	@ApiAuthenticated
	def setInstructions(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)
		instructionsFolder = skill.getResource(f'instructions/')
		instructionsFile = skill.getResource(f'instructions/{data["lang"]}.md')
		if not instructionsFolder.exists():
			instructionsFolder.mkdir(parents=True, exist_ok=True)
		if not instructionsFile.exists():
			instructionsFile.touch(exist_ok=True)
		instructionsFile.write_text(data['instruction'])

		return jsonify(success=True, instruction=instructionsFile.read_text() if instructionsFile.exists() else '')


	@route('/<skillName>/getDialogTemplate/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def getTemplate(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)
		allLang = {}
		tempOut = ""

		if not 'lang' in data:
			fp = skill.getResource('dialogTemplate')
			if fp.exists():
				for file in fp.glob('*.json'):
					allLang[Path(file).stem] = json.loads(file.read_text())

		else:
			dialogTemplate = skill.getResource(f'dialogTemplate/{data["lang"]}.json')
			if not dialogTemplate.exists():
				dialogTemplate = skill.getResource(f'dialogTemplate/en.json')
			tempOut = json.loads(dialogTemplate.read_text()) if dialogTemplate.exists() else ''

		return jsonify(success=True, dialogTemplate=tempOut, dialogTemplates=allLang)


	@route('/<skillName>/setDialogTemplate/', methods=['PATCH'])
	@ApiAuthenticated
	def setTemplate(self, skillName: str):
		self.logInfo(f'DialogTemplate API access for skill {skillName}')
		if skillName not in self.SkillManager.allSkills:
			self.logError(f'Skill {skillName} not found')
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		dialogTemplate = skill.getResource(f'dialogTemplate/{data["lang"]}.json')
		if not dialogTemplate.exists():
			dialogTemplate.touch(exist_ok=True)
		dialogTemplate.write_text(json.dumps(data['dialogTemplate'], indent=2))

		return jsonify(success=True, dialogTemplate=json.loads(dialogTemplate.read_text()) if dialogTemplate.exists() else '')


	@route('/<skillName>/setConfigTemplate/', methods=['PATCH'])
	@ApiAuthenticated
	def setConfig(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		configTemplate = skill.getResource(f'config.json.template')
		if not configTemplate.exists():
			configTemplate.touch(exist_ok=True)
		configTemplate.write_text(json.dumps(data['configTemplate'], indent=2))
		self.ConfigManager.loadCheckAndUpdateSkillConfigurations(skillToLoad=skillName)

		return jsonify(success=True, configTemplate=skill.getSkillConfigsTemplate())


	@route('/<skillName>/getTalkFiles/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def getTalkFiles(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		skill = self.SkillManager.getSkillInstance(skillName=skillName)
		talkFiles = dict()

		fp = skill.getResource('talks')
		if fp.exists():
			for file in fp.glob('*.json'):
				talkFiles[Path(file).stem] = json.loads(file.read_text())

		return jsonify(success=True, talkFiles=talkFiles)


	@route('/<skillName>/setTalkFile/', methods=['PATCH'])
	@ApiAuthenticated
	def setTalkFile(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		talkFile = skill.getResource(f'talks/{data["lang"]}.json')
		if not talkFile.exists():
			talkFile.touch(exist_ok=True)
		talkFile.write_text(json.dumps(data['talkFile'], indent=2))

		return jsonify(success=True, talkFile=talkFile.read_text() if talkFile.exists() else '')


	@route('/<skillName>/getInstallFile/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def getInstallFile(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		installFile = skill.getResource(f'{skillName}.install')

		return jsonify(success=True, installFile=json.loads(installFile.read_text()))


	@route('/<skillName>/setInstallFile/', methods=['PATCH'])
	@ApiAuthenticated
	def setInstallFile(self, skillName: str):
		self.logInfo(f'installFile API access for skill {skillName}')
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		installFile = skill.getResource(f'{skillName}.install')
		if not installFile.exists():
			installFile.touch(exist_ok=True)
		installFile.write_text(json.dumps(data['installFile'], indent=2))

		return jsonify(success=True, installFile=json.loads(installFile.read_text()) if installFile.exists() else '')
