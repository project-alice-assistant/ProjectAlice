# -*- coding: utf-8 -*-

import json
import os
import requests
import urllib.request

from terminaltables import DoubleTable

from core.console.Command import Command
from core.console.input.InputArgument import InputArgument
from core.console.input.InputOption import InputOption
from core.snips.SamkillaManager import SamkillaManager
from core.base.ModuleManager import ModuleManager
from core.snips.SnipsConsoleManager import SnipsConsoleManager
from core.voice.LanguageManager import LanguageManager
from core.util.ThreadManager import ThreadManager
from core.util.DatabaseManager import DatabaseManager
from core.dialog.ProtectedIntentManager import ProtectedIntentManager
from core.user.UserManager import UserManager
from core.base.model.GithubCloner import GithubCloner

#
# ModuleInstallCommand download a module from dedicated repository
#
class ModuleInstallCommand(Command):

	def create(self):
		self.setName('module:install')
		self.setDescription('Download and install module from dedicated repository')
		self.setDefinition([
			InputArgument(name='modulePath', mode=InputArgument.REQUIRED, description='Module path (e.g. ProjectAlice/AliceCore)'),
		])
		self.setHelp('> The %command.name% download and install a module from dedicated repository:\n'
					 '  <fg:magenta>%command.full_name%<fg:reset> <fg:cyan>author/moduleName<fg:reset>')

	def execute(self, input):
		modulePath = input.getArgument('modulePath')
		parts = modulePath.split("/")

		TABLE_DATA = [['Module Installer']]
		table_instance = DoubleTable(TABLE_DATA)
		self.write('\n' + table_instance.table + '\n', 'yellow')

		if len(parts) != 2:
			self.write('> Unknown <fg:red>' + modulePath + '<fg:reset> pair')
			self.write('- Correct format is <fg:yellow>module:install author/moduleName<fg:reset>\n')
			return

		author, moduleName = parts

		try:
			url = ModuleManager.GITHUB_BARE_BASE_URL + '/' + modulePath + '/' + moduleName + '.install'
			req = requests.get(url)

			if req.status_code // 100 == 4:
				self.write('> Unknown <fg:red>' + modulePath + '<fg:reset> pair')
				self.write('- You can use <fg:yellow>author:list<fg:reset> to list all authors')
				self.write('- You can use <fg:yellow>module:list authorName<fg:reset> to list all modules from an author\n')
				return

			result = req.content
			module = json.loads(result.decode())

			self.write('+ Informations:')
			self.write('===============')
			self.write('name: <fg:yellow>'+str(module['name'])+'<fg:reset>')
			self.write('version: <fg:yellow>'+str(module['version'])+'<fg:reset>')
			self.write('author: <fg:yellow>'+module['author']+'<fg:reset>')
			self.write('maintainers: <fg:yellow>'+', '.join(module['maintainers'])+'<fg:reset>')
			self.write('description: <fg:yellow>'+module['desc']+'<fg:reset>')
			self.write('aliceMinVersion: <fg:yellow>'+module['aliceMinVersion']+'<fg:reset>')
			self.write('pip requirements: <fg:yellow>'+', '.join(module['pipRequirements'])+'<fg:reset>')
			self.write('system requirements: <fg:yellow>'+', '.join(module['systemRequirements'])+'<fg:reset>')
			self.nl()
			self.write('+ Conditions:')
			self.write('=============')
			self.write('lang: <fg:yellow>'+', '.join(module['conditions']['lang'])+'<fg:reset>')

			urllib.request.urlretrieve(url, "system/moduleInstallTickets/" + moduleName + '.install')


		except Exception:
			self.write('Error listing authors', 'red')
			raise

		self.nl()
