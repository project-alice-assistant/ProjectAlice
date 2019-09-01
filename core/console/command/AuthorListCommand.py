# -*- coding: utf-8 -*-

import json

import requests
from terminaltables import DoubleTable

from core.base.ModuleManager import ModuleManager
from core.console.Command import Command


#
# AuthorListCommand list authors from dedicated repository
#
class AuthorListCommand(Command):


	def create(self):
		self.setName('author:list')
		self.setDescription('List authors from dedicated repository')
		self.setDefinition()
		self.setHelp('> The %command.name% list authors from dedicated repository:\n'
					 '  <fg:magenta>%command.full_name%<fg:reset>')

	def execute(self, input):
		TABLE_DATA = [['Authors List']]
		table_instance = DoubleTable(TABLE_DATA)
		self.write('\n' + table_instance.table + '\n', 'magenta')

		TABLE_DATA = [['Name']]
		table_instance = DoubleTable(TABLE_DATA)

		try:
			req = requests.get('https://api.github.com/' + ModuleManager.GITHUB_API_BASE_URL)

			if req.status_code == 403:
				self.write('<bg:red> Github API quota limitations reached<bg:reset>\n')
				return

			result = req.content
			authors = json.loads(result.decode())

			for author in authors:
				TABLE_DATA.append([
					author['name'],
				])

		except Exception:
			self.write('Error listing authors', 'red')
			raise


		self.write(table_instance.table)
