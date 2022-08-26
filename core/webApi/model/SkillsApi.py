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
import re
from flask import Response, jsonify, request
from flask_classful import route
from pathlib import Path

from AliceGit.Exceptions import GithubRepoNotFound, GithubUserNotFound, NotGitRepository, RemoteAlreadyExists, GithubCreateFailed
from AliceGit.Git import Repository
from AliceGit.Github import Github
from core.util.Decorators import ApiAuthenticated
from core.webApi.model.Api import Api


class SkillsApi(Api):
	route_base = f'/api/{Api.version()}/skills/'

	@route('/')
	def index(self):
		return jsonify(skills={skillName: skill.toDict() for skillName, skill in self.SkillManager.allSkills.items()})

	# noinspection PyMethodMayBeStatic
	def skillNotFound(self) -> Response:
		return jsonify(success=False, reason='skill not found')

	# noinspection PyMethodMayBeStatic
	def githubMissing(self) -> Response:
		return jsonify(success=False, reason='github auth not found')

	@ApiAuthenticated
	def delete(self, skillName: str) -> Response:
		if skillName in self.SkillManager.neededSkills:
			return jsonify(success=False, reason='skill cannot be deleted')

		try:
			self.SkillManager.removeSkill(skillName)
			return jsonify(success=True)
		except Exception as e:
			return jsonify(success=False, reason=f'Failed deleting skill: {e}')

	@route('/getStore/')
	def getStore(self) -> Response:
		return jsonify(store=self.SkillStoreManager.getStoreData())

	@ApiAuthenticated
	@route('/createSkill/', methods=['PUT'])
	def createSkill(self) -> Response:
		try:
			newSkill = {
				'name': request.form.get('name', ''),
				'speakableName': request.form.get('speakableName', ''),
				'description': request.form.get('description', 'Missing description'),
				'category': request.form.get('category', 'undefined'),
				'fr': request.form.get('fr', False),
				'de': request.form.get('de', False),
				'it': request.form.get('it', False),
				'pl': request.form.get('pl', False),
				'widgets': request.form.get('widgets', ''),
				'nodes': request.form.get('nodes', ''),
				'devices': request.form.get('devices', ''),
				'icon': request.form.get('icon', 'fas fa-biohazard')
			}

			if not self.SkillManager.createNewSkill(newSkill):
				raise Exception

			self.SkillManager.initSkills(onlyInit=newSkill['name'])
			skill = self.SkillManager.getSkillInstance(skillName=newSkill['name'])
			return jsonify(success=True, skill=skill.toDict() if skill else dict())

		except Exception as e:
			self.logError(f'Something went wrong creating a new skill: {e}')
			return jsonify(success=False, message=str(e))

	@ApiAuthenticated
	@route('/installSkills/', methods=['PUT'])
	def installSkills(self) -> Response:
		try:
			skills = request.json

			status = dict()
			for skill in skills:
				try:
					self.SkillManager.installSkills(skills=skill, startSkill=True)
					status[skill] = 'ok'
				except:
					status[skill] = 'nok'

			self.AssistantManager.checkAssistant()
			return jsonify(success=True, status=status)
		except Exception as e:
			self.logWarning(f'Failed installing skill: {e}', printStack=True)
			return jsonify(success=False, message=str(e))

	@ApiAuthenticated
	def put(self, skillName: str) -> Response:
		try:
			self.SkillManager.installSkills(skills=skillName, startSkill=True)
			self.AssistantManager.checkAssistant()
		except Exception as e:
			self.logWarning(f'Failed installing skill: {e}', printStack=True)
			return jsonify(success=False, message=str(e))

		return jsonify(success=True)

	@route('/<skillName>/', methods=['PATCH'])
	@ApiAuthenticated
	def saveSkillSettings(self, skillName: str) -> Response:
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
	def get(self, skillName: str) -> Response:
		try:
			skill = self.SkillManager.getSkillInstance(skillName=skillName, silent=True)
			if not skill:
				skill = self.SkillManager.allSkills.get(skillName, dict())
				if isinstance(skill, dict):
					raise Exception('Skill not found')

			return jsonify(success=True, skill=skill.toDict())
		except Exception as e:
			self.logWarning(f'Failed fetching skill: {e}', printStack=True)
			return jsonify(success=False, message=str(e))

	@route('/<skillName>/toggleActiveState/')
	@ApiAuthenticated
	def toggleActiveState(self, skillName: str) -> Response:
		try:
			if skillName not in self.SkillManager.allSkills:
				return self.skillNotFound()

			if self.SkillManager.isSkillActive(skillName):
				if skillName in self.SkillManager.neededSkills:
					return jsonify(success=False, message='Required skill cannot be deactivated!')

				result = self.SkillManager.deactivateSkill(skillName=skillName, persistent=True)
			else:
				result = self.SkillManager.activateSkill(skillName=skillName, persistent=True)

			return jsonify(success=result)
		except Exception as e:
			self.logWarning(f'Failed toggling skill: {e}', printStack=True)
			return jsonify(success=False, message=str(e))

	@route('/<skillName>/activate/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def activate(self, skillName: str) -> Response:
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
	def deactivate(self, skillName: str) -> Response:
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
	def reload(self, skillName: str) -> Response:
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

	@route('/<skillName>/checkUpdate/')
	@ApiAuthenticated
	def checkUpdate(self, skillName: str) -> Response:
		"""
		check for updates for the specified skill
		:param skillName:
		:return:
		"""
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		updated = False
		update = self.SkillManager.checkForSkillUpdates(skillToCheck=skillName)
		if update:
			self.SkillManager.updateSkills(skills=update)
			updated = True

		return jsonify(success=True, updated=updated)

	@route('/<skillName>/isDirty/', methods=['GET'])
	@ApiAuthenticated
	def isDirty(self, skillName: str) -> Response:
		try:
			repo = self.SkillManager.getSkillRepository(skillName=skillName)
			if repo.isDirty():
				return jsonify(success=True, message='dirty')
			else:
				return jsonify(success=True, message='clean')
		except NotGitRepository:
			return jsonify(success=True, message='dirty')

	@route('/<skillName>/setModified/')
	@ApiAuthenticated
	def setModified(self, skillName: str) -> Response:
		"""
		sets the modified status for that skill.
		creates a private repository for the user and checks out the fork
		:param skillName:
		:return:
		"""
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		if not self.ConfigManager.githubAuth:
			return self.githubMissing()

		try:
			auth = self.ConfigManager.githubAuth
			github = Github(username=auth[0],
							token=auth[1],
							repositoryName=f'skill_{skillName}',
							createRepository=True)

			repo = self.SkillManager.getSkillRepository(skillName=skillName)
			repo.remoteAdd(url=github.usersUrl, name='AliceSK')
		except GithubUserNotFound:
			return jsonify(success=False, reason='Github user not existing')

		return jsonify(success=True)

	@route('/<skillName>/checkout/<remote>/<branch>/')
	@ApiAuthenticated
	def checkout(self, skillName: str, remote: str, branch: str) -> Response:
		"""
		checkout the given remote
		:param skillName:
		:param remote:
		:param branch:
		:return:
		"""
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		repository = Repository(directory=self.SkillManager.getSkillDirectory(skillName=skillName), init=False,
								raiseIfExisting=False)
		repository.clean()
		repository.setUpstream(branch=branch, remote=remote)
		repository.reset(f'{remote}/{branch}')
		return jsonify(success=True)

	@route('/<skillName>/revert/')
	@ApiAuthenticated
	def revert(self, skillName: str) -> Response:
		"""
		reverts the skill to its official state. Removes the "modified" status and runs an update.
		:param skillName:
		:return:
		"""
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		skill = self.SkillManager.getSkillInstance(skillName=skillName)
		skill.repository.revert()
		skill.repository.checkout(tag=self.SkillStoreManager.getSkillUpdateTag(skillName=skillName), force=True)
		return self.checkUpdate(skillName)

	@route('/<skillName>/upload/')
	@ApiAuthenticated
	def upload(self, skillName: str) -> Response:
		"""
		upload the skill to the private repository.
		Will create a repository if required, add all untracked changes, create a commit and push
		:param skillName:
		:return:
		"""
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		installFilePath = self.SkillManager.getSkillInstallFilePath(skillName=skillName)
		try:
			repository = Repository(directory=self.SkillManager.getSkillDirectory(skillName=skillName), init=True,
									raiseIfExisting=False)

			auth = self.ConfigManager.githubAuth
			github = Github(username=auth[0], token=auth[1], repositoryName=f'skill_{skillName}', createRepository=True)
			try:
				repository.remoteAdd(url=github.usersUrl, name='AliceSK')
			except RemoteAlreadyExists as e:
				self.logInfo(f'Error uploading to git: {e}')

			if repository.isDirty():
				if not repository.commit(message='Save through Alice web UI', autoAdd=True):
					self.logError('Commit failed!')
			else:
				self.logInfo('Nothing to commit')

			out, err = repository.push()
			self.logInfo(out)
			self.logError(err)
		except GithubUserNotFound:
			return jsonify(success=False, message='The provided Github user is not existing')
		except GithubRepoNotFound:
			if not self.SkillManager.uploadSkillToGithub(skillName=skillName,
														 skillDesc=json.loads(installFilePath.read_text())['desc']):
				return jsonify(success=False, message='Failed uploading to Github')
		except GithubCreateFailed as e:
			self.logError(e)
			return jsonify(success=False, message=str(e))
		return jsonify(success=True)

	@route('/<skillName>/gitStatus/')
	@ApiAuthenticated
	def getGitStatus(self, skillName: str) -> Response:
		"""
		returns a list containing the public and private GitHub URL of that skill.
		The repository does not have to exist yet!
		The current status of the repository is included as well
		Currently possible status: True/False
		:param skillName:
		:return:
		"""

		skill = self.SkillManager.getSkillInstance(skillName=skillName)
		if not skill:
			return self.skillNotFound()

		try:
			git = Repository(directory=skill.skillPath)
		except NotGitRepository as e:
			return jsonify(success=False, noGit=True, message=str(e))

		try:
			auth = self.ConfigManager.githubAuth
			Github(username=auth[0], token=auth[1], repositoryName=f'skill_{skillName}')
		except Exception as e:
			if len(git.remote) > 0:
				return jsonify(success=False, message=str(e))
			else:
				return jsonify(success=False, noRemote=True, message=str(e))

		res = dict()
		for name, rem in git.remote.items():
			status = Github.getStatusForUrl(url=rem.url, silent=True) is not False
			res[name] = {'repoType': 'Public' if name == 'project-alice-assistant' else 'Private',
						 'name': rem.name,
						 'url': re.sub(r"https:\/\/.*:(.*)@github\.com\/", 'https://github.com/', rem.url),
						 'user': name,
						 'status': status,
						 'commitsBehind': rem.getCommitCount() if status else '-1',
						 'commitsAhead': rem.getCommitCount(ahead=False) if status else '-1',
						 'lsRemote': rem.lsRemote(tags=False)}

		changes = git.status().changes()

		return jsonify(success=True, result=res, changes=changes, upstream=git.status().getUpstream())

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
	def setInstructions(self, skillName: str) -> Response:
		"""
		overwrite the instructions of a skill and defined language
		:param skillName:
		:return:
		"""
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
	def getTemplate(self, skillName: str) -> Response:
		"""
		get the dialog template for one or all languages for a given skill.
		When no language is specified all are returned
		:param skillName:
		:return:
		"""
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)
		allLang = dict()
		tempOut = ''

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
	def setTemplate(self, skillName: str) -> Response:
		"""
		overwrite the dialog template of a skill for a given language
		:param skillName:
		:return:
		"""
		self.logDebug(f'DialogTemplate API access for skill {skillName}')
		if skillName not in self.SkillManager.allSkills:
			self.logError(f'Skill {skillName} not found')
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		dialogTemplate = skill.getResource(f'dialogTemplate/{data["lang"]}.json')
		if not dialogTemplate.exists():
			dialogTemplate.touch(exist_ok=True)
		dialogTemplate.write_text(json.dumps(data['dialogTemplate'], indent='\t', ensure_ascii=False))

		return jsonify(success=True,
					   dialogTemplate=json.loads(dialogTemplate.read_text()) if dialogTemplate.exists() else '')

	@route('/<skillName>/setConfigTemplate/', methods=['PATCH'])
	@ApiAuthenticated
	def setConfig(self, skillName: str) -> Response:
		"""
		write the config template for a skill
		:param skillName:
		:return:
		"""
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		configTemplate = skill.getResource(f'config.json.template')
		if not configTemplate.exists():
			configTemplate.touch(exist_ok=True)
		configTemplate.write_text(json.dumps(data['configTemplate'], indent='\t', ensure_ascii=False))
		self.ConfigManager.loadCheckAndUpdateSkillConfigurations(skillToLoad=skillName)

		return jsonify(success=True, configTemplate=skill.getSkillConfigsTemplate())

	@route('/<skillName>/getTalkFiles/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def getTalkFiles(self, skillName: str) -> Response:
		"""
		get the talk files for all languages of one skill
		:param skillName:
		:return:
		"""
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		skill = self.SkillManager.getSkillInstance(skillName=skillName)
		talkFiles = dict()

		fp = skill.getResource('talks')
		if fp.exists():
			for file in fp.glob('*.json'):
				talkFiles[Path(file).stem] = json.loads(file.read_text())
		if talkFiles:
			return jsonify(success=True, talkFiles=talkFiles)
		else:
			return jsonify(success=False, message='no talkfile found.')

	@route('/<skillName>/getTalkTopics/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def getTalkTopics(self, skillName: str) -> Response:
		"""
		get the talk topics for one skill
		:param skillName:
		:return:
		"""
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		fp = skill.getResource(f'talks/{self.LanguageManager.activeLanguage}.json')
		if fp.exists():
			talkFile = json.loads(fp.read_text())
		else:
			talkFile = list()

		return jsonify(success=True, talkTopics=list(talkFile))

	@route('/<skillName>/setTalkFile/', methods=['PATCH'])
	@ApiAuthenticated
	def setTalkFile(self, skillName: str) -> Response:
		"""
		overwrite the talk file of a given skill and language
		:param skillName:
		:return:
		"""
		self.logDebug(f'Writing talkFile API access for skill {skillName}')
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		talkFile = skill.getResource(f'talks/{data["lang"]}.json')
		if not talkFile.exists():
			talkFile.touch(exist_ok=True)
		talkFile.write_text(json.dumps(data['talkFile'], indent='\t', ensure_ascii=False))

		return jsonify(success=True, talkFile=talkFile.read_text() if talkFile.exists() else '')

	@route('/<skillName>/getInstallFile/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def getInstallFile(self, skillName: str) -> Response:
		"""
		read the *.install file of a given skill
		:param skillName:
		:return:
		"""
		try:
			installFile = self.SkillManager.getSkillInstallFilePath(skillName=skillName)
			if not installFile.exists:
				raise Exception
			return jsonify(success=True, installFile=json.loads(installFile.read_text()))
		except:
			return self.skillNotFound()

	@route('/<skillName>/setInstallFile/', methods=['PATCH'])
	@ApiAuthenticated
	def setInstallFile(self, skillName: str) -> Response:
		"""
		Change the *.install file of a skill, overwrites everything with the values given.
		:param skillName:
		:return:
		"""
		self.logDebug(f'InstallFile API access for skill {skillName}')
		if skillName not in self.SkillManager.allSkills:
			return self.skillNotFound()

		data = request.json
		skill = self.SkillManager.getSkillInstance(skillName=skillName)

		installFile = skill.getResource(f'{skillName}.install')
		if not installFile.exists():
			installFile.touch(exist_ok=True)
		installFile.write_text(json.dumps(data['installFile'], indent='\t', ensure_ascii=False))

		return jsonify(success=True, installFile=json.loads(installFile.read_text()) if installFile.exists() else '')

	@route('/<skillName>/createWidget/<widgetName>/', methods=['PATCH'])
	@ApiAuthenticated
	def createWidget(self, skillName: str, widgetName: str) -> Response:
		"""
		Create the empty hull for a new widget in the skills folders
		:param widgetName:
		:param skillName:
		:return:
		"""
		self.logDebug(f'Creating new widget {widgetName} for skill {skillName}')
		try:
			dest = self.getSkillDest(skillName=skillName)
			self.Commons.runSystemCommand(['./venv/bin/pip', 'install', '--upgrade', 'projectalice-sk'])
			self.Commons.runSystemCommand(['./venv/bin/projectalice-sk', 'createwidget', '--widget', widgetName, '--path', f'{dest}'])
			return jsonify(success=True)
		except:
			return self.skillNotFound()

	@route('/<skillName>/createDeviceType/<deviceName>/', methods=['PATCH'])
	@ApiAuthenticated
	def createDeviceType(self, skillName: str, deviceName: str) -> Response:
		"""
		Create the empty hull for a new device type in the skills folders
		:param deviceName:
		:param skillName:
		:return:
		"""
		self.logDebug(f'Creating new device type {deviceName} for skill {skillName}')
		try:
			dest = self.getSkillDest(skillName=skillName)
			self.Commons.runSystemCommand(['./venv/bin/pip', 'install', '--upgrade', 'projectalice-sk'])
			self.Commons.runSystemCommand(['./venv/bin/projectalice-sk', 'createdevicetype', '--device', deviceName, '--path', f'{dest}'])
			return jsonify(success=True)
		except:
			return self.skillNotFound()

	def getSkillDest(self, skillName: str):
		"""
		Returns skill resource
		:param skillName:
		:return:
		"""
		try:
			return self.SkillManager.allSkills.get(skillName, None).getResource()
		except:
			raise  # Let caller handle it
