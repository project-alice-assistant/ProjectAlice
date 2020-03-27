from flask import jsonify, render_template, request

from core.base.model.Version import Version
from core.commons import constants
from core.interface.model.View import View


class SkillsView(View):
	route_base = '/skills/'


	def index(self):
		skills = {skillName: skill for skillName, skill in sorted(self.SkillManager.allWorkingSkills.items()) if skill is not None}

		return render_template(template_name_or_list='skills.html',
		                       skills=skills,
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	def toggleSkill(self):
		try:
			_, skill = request.form.get('id').split('_')
			self.SkillManager.toggleSkillState(skillName=skill, persistent=True)
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


	def reloadSkill(self):
		try:
			_, skill = request.form.get('id').split('_')
			self.SkillManager.reloadSkill(skill)
		except Exception as e:
			self.logWarning(f'Failed reloading skill: {e}', printStack=True)

		return self.index()


	def saveSkillSettings(self):
		skillName = request.form['skillName']
		for confName, confValue in request.form.items():
			if confName == 'skillName':
				continue

			self.ConfigManager.updateSkillConfigurationFile(
				skillName=skillName,
				key=confName,
				value=confValue
			)

		return self.index()


	def updateSkill(self):
		_, author, skill = request.form.get('id').split('_')

		try:
			self.WebInterfaceManager.newSkillInstallProcess(skill)
			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f'Failed updating skill: {e}', printStack=True)
			self.WebInterfaceManager.skillInstallProcesses[skill['skill']]['status'] = 'failed'
			return jsonify(success=False)


	def installSkills(self):
		try:
			skills = request.json

			for skill in skills:
				self.WebInterfaceManager.newSkillInstallProcess(skill['skill'])
				if not self.SkillManager.downloadInstallTicket(skill['skill']):
					self.WebInterfaceManager.skillInstallProcesses[skill['skill']]['status'] = 'failed'
					continue

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f'Failed installing skill: {e}', printStack=True)
			return jsonify(success=False)


	def checkInstallStatus(self):
		skill = request.form.get('skill')
		status = self.WebInterfaceManager.skillInstallProcesses.get(skill, {'status': 'unknown'})['status']
		return jsonify(status)


	def loadStoreData(self):
		self.SkillStoreManager.refreshStoreData()
		skillStoreData = self.SkillStoreManager.skillStoreData
		activeLanguage = self.LanguageManager.activeLanguage.lower()
		aliceVersion = Version.fromString(constants.VERSION)
		supportedSkillStoreData = dict()

		for skillName, skillInfo in skillStoreData.items():
			if self.SkillManager.getSkillInstance(skillName=skillName, silent=True) \
					or ('lang' in skillInfo['conditions'] and activeLanguage not in skillInfo['conditions']['lang']):
				continue

			version = Version()
			for aliceMinVersion, skillVersion in skillInfo['versionMapping'].items():
				if Version.fromString(aliceMinVersion) > aliceVersion:
					continue

				skillRepoVersion = Version.fromString(skillVersion)

				if skillRepoVersion > version:
					version = skillRepoVersion

			skillInfo['version'] = str(version)
			supportedSkillStoreData[skillName] = skillInfo

		return supportedSkillStoreData
