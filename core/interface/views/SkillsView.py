import json
from pathlib import Path

import requests
from flask import jsonify, render_template, request

from core.base.model.GithubCloner import GithubCloner
from core.base.model.Version import Version
from core.commons import constants
from core.interface.model.View import View


class SkillsView(View):
	route_base = '/skills/'


	def index(self):
		skills = {**self.SkillManager.activeSkills, **self.SkillManager.deactivatedSkills}
		skills = {skillName: skill for skillName, skill in sorted(skills.items()) if skill is not None}

		return render_template(template_name_or_list='skills.html',
		                       skills=skills,
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	def toggleSkill(self):
		try:
			_, skill = request.form.get('id').split('_')
			if self.SkillManager.isSkillActive(skill):
				self.SkillManager.deactivateSkill(skillName=skill, persistent=True)
			else:
				self.SkillManager.activateSkill(skillName=skill, persistent=True)
		except Exception as e:
			self.logWarning(f'Failed toggling skill: {e}', printStack=True)

		return self.index()


	def deleteSkill(self):
		try:
			_, skill = request.form.get('id').split('_')
			self.SkillManager.removeSkill(skill)
		except Exception as e:
			self.logWarning(f'Failed deleting skill: {e}', printStack=True)

		return self.index()


	def saveSkillSettings(self):
		skillName = request.form['skillName']
		for confName, confValue in request.form.items():
			if confName == 'skillName':
				continue

			if confValue == 'on':
				confValue = True
			elif confValue == 'off':
				confValue = False

			self.ConfigManager.updateSkillConfigurationFile(
				skillName=skillName,
				key=confName,
				value=confValue
			)

		return self.index()


	def installSkills(self):
		try:
			skills = request.json

			for skill in skills:
				self.WebInterfaceManager.newSkillInstallProcess(skill['skill'])
				req = requests.get(f'https://raw.githubusercontent.com/project-alice-assistant/ProjectAliceModules/{self.ConfigManager.getSkillsUpdateSource()}/PublishedSkills/{skill["author"]}/{skill["skill"]}/{skill["skill"]}.install')
				remoteFile = req.json()
				if not remoteFile:
					self.WebInterfaceManager.skillInstallProcesses[skill['skill']]['status'] = 'failed'
					continue

				skillFile = Path(self.Commons.rootDir(), f'system/skillInstallTickets/{skill["skill"]}.install')
				skillFile.write_text(json.dumps(remoteFile))

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f'Failed installing skill: {e}', printStack=True)
			return jsonify(success=False)


	def checkInstallStatus(self):
		skill = request.form.get('skill')
		status = self.WebInterfaceManager.skillInstallProcesses.get(skill, {'status': 'unknown'})['status']
		return jsonify(status)


	def loadStoreData(self):
		installers = dict()
		updateSource = self.ConfigManager.getSkillsUpdateSource()
		req = requests.get(
			url='https://api.github.com/search/code?q=extension:install+repo:project-alice-assistant/ProjectAliceModules/',
			auth=GithubCloner.getGithubAuth())
		results = req.json()
		if results:
			for skill in results['items']:
				try:
					req = requests.get(
						url=f"{skill['url'].split('?')[0]}?ref={updateSource}",
						headers={'Accept': 'application/vnd.github.VERSION.raw'},
						auth=GithubCloner.getGithubAuth()
					)
					installer = req.json()
					if installer:
						installers[installer['name']] = installer

				except Exception:
					continue

		actualVersion = Version(constants.VERSION)
		return {
			skillName: skillInfo for skillName, skillInfo in installers.items()
			if self.SkillManager.getSkillInstance(skillName=skillName, silent=True) is None and actualVersion >= Version(skillInfo['aliceMinVersion'])
		}
