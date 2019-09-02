# -*- coding: utf-8 -*-

import json

import requests
from terminaltables import DoubleTable

from core.base.ModuleManager import ModuleManager
from core.console.Command import Command
from core.console.input.InputArgument import InputArgument
from core.console.input.InputOption import InputOption


#
# ModuleListCommand list modules from dedicated repository
#
class ModuleListCommand(Command):
	DESCRIPTION_MAX = 100


	def create(self):
		self.setName('module:list')
		self.setDescription('List remote modules from dedicated repository created by a specific author')
		self.setDefinition([
			InputArgument(name='authorName', mode=InputArgument.REQUIRED, description='Author\'s name'),
			InputOption(name='--full', shortcut='-f', mode=InputOption.VALUE_NONE, description='Display full description instead of truncated one'),

		])
		self.setHelp('> The %command.name% list modules from dedicated repository created by a specific author:\n'
					 '  <fg:magenta>%command.full_name%<fg:reset> <fg:cyan>authorName<fg:reset> <fg:yellow>[-f|--full]<fg:reset>')


	def execute(self, inputt):
		TABLE_DATA = [['Modules created by ' + inputt.getArgument('authorName')]]
		table_instance = DoubleTable(TABLE_DATA)
		self.write('\n' + table_instance.table + '\n', 'yellow')

		TABLE_DATA = [['Name', 'Version', 'Langs', 'Description']]
		table_instance = DoubleTable(TABLE_DATA)

		try:
			req = requests.get('https://api.github.com/' + ModuleManager.GITHUB_API_BASE_URL + '/' + inputt.getArgument('authorName'))

			if req.status_code == 403:
				self.write('<bg:red> Github API quota limitations reached<bg:reset>\n')
				return
			elif req.status_code // 100 == 4:
				self.write('> Unknown author <fg:red>' + inputt.getArgument('authorName') + '<fg:reset>')
				self.write('- You can use <fg:yellow>author:list<fg:reset> to list all authors\n')
				return

			result = req.content
			modules = json.loads(result.decode())

			for module in modules:
				moduleInstallFile = module['html_url'] \
										.replace('github.com', 'raw.githubusercontent.com') \
										.replace('/blob', '') \
										.replace('/tree', '') \
									+ '/' + module['name'] + '.install'

				try:
					req = requests.get(moduleInstallFile)
					result = req.content
					moduleDetails = json.loads(result.decode())
					tLangs = '|'.join(moduleDetails['conditions']['lang']) if 'lang' in moduleDetails['conditions'] else '-'
					tDesc = moduleDetails['desc']

					if not inputt.getOption('full'):
						tDesc = (tDesc[:self.DESCRIPTION_MAX] + '..') if len(tDesc) > self.DESCRIPTION_MAX else tDesc

					TABLE_DATA.append([
						moduleDetails['name'],
						moduleDetails['version'],
						tLangs,
						tDesc
					])

				except Exception:
					self.write('Error get module {}'.format(module['name']), 'red')
					raise

		except Exception:
			self.write('Error listing modules', 'red')
			raise

		self.write(table_instance.table)
